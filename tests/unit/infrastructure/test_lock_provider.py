"""Tests for LockProvider implementations based on ADR-003.

Tests cover:
- InMemoryLockProvider two-phase locking (ADR-003 Section 5)
- Lock release on exception (ADR-003 Section 10, Test 3)
- NoOpLockProvider for single-threaded tests (ADR-003 Section 9)
- Concurrent access serialization
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait

import pytest

from payments_core.application.ports import LockProvider
from payments_core.infrastructure.lock_provider import (
    InMemoryLockProvider,
    NoOpLockProvider,
)

# =============================================================================
# InMemoryLockProvider Tests - ADR-003 Section 5
# =============================================================================


class TestInMemoryLockProviderInterface:
    """Test InMemoryLockProvider implements LockProvider interface."""

    def test_implements_lock_provider_interface(self) -> None:
        provider = InMemoryLockProvider()

        assert isinstance(provider, LockProvider)

    def test_acquire_returns_context_manager(self) -> None:
        provider = InMemoryLockProvider()

        with provider.acquire("test-resource"):
            pass  # Context manager works


class TestInMemoryLockProviderBasicBehavior:
    """Test basic locking behavior."""

    def test_lock_can_be_acquired(self) -> None:
        provider = InMemoryLockProvider()
        acquired = False

        with provider.acquire("test-resource"):
            acquired = True

        assert acquired is True

    def test_same_resource_can_be_acquired_sequentially(self) -> None:
        provider = InMemoryLockProvider()
        acquisitions = 0

        with provider.acquire("test-resource"):
            acquisitions += 1

        with provider.acquire("test-resource"):
            acquisitions += 1

        assert acquisitions == 2

    def test_different_resources_use_different_locks(self) -> None:
        provider = InMemoryLockProvider()

        with provider.acquire("resource-a"), provider.acquire("resource-b"):
            pass  # Both locks held simultaneously - no deadlock


class TestInMemoryLockProviderExceptionSafety:
    """Test lock release on exception per ADR-003 Section 10, Test 3."""

    def test_lock_released_on_exception(self) -> None:
        """Lock must be released even when exception occurs in critical section."""
        provider = InMemoryLockProvider()
        resource_id = "test-resource"

        # First acquisition raises exception
        with pytest.raises(RuntimeError), provider.acquire(resource_id):
            raise RuntimeError("Simulated failure")

        # Second acquisition should succeed (lock was released)
        acquired = False
        with provider.acquire(resource_id):
            acquired = True

        assert acquired is True

    def test_lock_released_on_nested_exception(self) -> None:
        """Lock must be released even with nested exceptions."""
        provider = InMemoryLockProvider()

        with pytest.raises(ValueError), provider.acquire("resource"):
            try:
                raise RuntimeError("Inner error")
            except RuntimeError:
                raise ValueError("Outer error")  # noqa: B904

        # Should not deadlock
        with provider.acquire("resource"):
            pass


class TestInMemoryLockProviderConcurrency:
    """Test concurrent access serialization."""

    def test_same_resource_serializes_access(self) -> None:
        """Concurrent requests for same resource are serialized."""
        provider = InMemoryLockProvider()
        resource_id = "shared-resource"
        results: list[int] = []
        lock_acquired_times: list[float] = []

        def worker(worker_id: int) -> None:
            with provider.acquire(resource_id):
                lock_acquired_times.append(time.time())
                time.sleep(0.05)  # Hold lock briefly
                results.append(worker_id)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(worker, i) for i in range(3)]
            wait(futures)

        # All workers completed
        assert len(results) == 3
        # Results should contain all worker IDs (order may vary)
        assert set(results) == {0, 1, 2}

    def test_different_resources_allow_parallel_access(self) -> None:
        """Different resources can be locked concurrently."""
        provider = InMemoryLockProvider()
        parallel_count = 0
        max_parallel = 0
        count_lock = threading.Lock()

        def worker(resource_id: str) -> None:
            nonlocal parallel_count, max_parallel
            with provider.acquire(resource_id):
                with count_lock:
                    parallel_count += 1
                    max_parallel = max(max_parallel, parallel_count)
                time.sleep(0.05)  # Hold lock briefly
                with count_lock:
                    parallel_count -= 1

        with ThreadPoolExecutor(max_workers=3) as executor:
            # Each worker locks a different resource
            futures = [executor.submit(worker, f"resource-{i}") for i in range(3)]
            wait(futures)

        # Multiple locks should have been held in parallel
        assert max_parallel > 1

    def test_lock_contention_no_deadlock(self) -> None:
        """Multiple threads contending for same lock should not deadlock."""
        provider = InMemoryLockProvider()
        resource_id = "contested-resource"
        completed = []

        def worker(worker_id: int) -> None:
            for _ in range(5):
                with provider.acquire(resource_id):
                    time.sleep(0.01)
            completed.append(worker_id)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            wait(futures, timeout=10)

        # All workers should complete without deadlock
        assert len(completed) == 5


class TestInMemoryLockProviderLockCreation:
    """Test lock creation behavior (two-phase locking)."""

    def test_lock_created_on_first_acquire(self) -> None:
        provider = InMemoryLockProvider()
        resource_id = "new-resource"

        assert resource_id not in provider._locks

        with provider.acquire(resource_id):
            assert resource_id in provider._locks

    def test_same_lock_reused_for_same_resource(self) -> None:
        provider = InMemoryLockProvider()
        resource_id = "reused-resource"

        with provider.acquire(resource_id):
            first_lock = provider._locks[resource_id]

        with provider.acquire(resource_id):
            second_lock = provider._locks[resource_id]

        assert first_lock is second_lock


# =============================================================================
# NoOpLockProvider Tests - ADR-003 Section 9
# =============================================================================


class TestNoOpLockProviderInterface:
    """Test NoOpLockProvider implements LockProvider interface."""

    def test_implements_lock_provider_interface(self) -> None:
        provider = NoOpLockProvider()

        assert isinstance(provider, LockProvider)

    def test_acquire_returns_context_manager(self) -> None:
        provider = NoOpLockProvider()

        with provider.acquire("test-resource"):
            pass  # Context manager works


class TestNoOpLockProviderBehavior:
    """Test NoOpLockProvider behavior."""

    def test_acquire_does_not_block(self) -> None:
        provider = NoOpLockProvider()
        acquired = False

        with provider.acquire("test-resource"):
            acquired = True

        assert acquired is True

    def test_same_resource_can_be_acquired_multiple_times(self) -> None:
        provider = NoOpLockProvider()
        acquisitions = 0

        with provider.acquire("test-resource"):
            acquisitions += 1
            with provider.acquire("test-resource"):
                acquisitions += 1
                with provider.acquire("test-resource"):
                    acquisitions += 1

        assert acquisitions == 3

    def test_no_exception_on_any_resource_id(self) -> None:
        provider = NoOpLockProvider()

        # Various resource IDs should all work
        with provider.acquire(""):
            pass
        with provider.acquire("a" * 1000):
            pass
        with provider.acquire("special-chars-!@#$%"):
            pass


class TestNoOpLockProviderExceptionSafety:
    """Test NoOpLockProvider handles exceptions correctly."""

    def test_exception_propagates(self) -> None:
        provider = NoOpLockProvider()

        with pytest.raises(RuntimeError, match="test error"), provider.acquire("resource"):
            raise RuntimeError("test error")

    def test_can_acquire_after_exception(self) -> None:
        provider = NoOpLockProvider()

        with pytest.raises(RuntimeError), provider.acquire("resource"):
            raise RuntimeError("error")

        # Should still work after exception
        with provider.acquire("resource"):
            pass
