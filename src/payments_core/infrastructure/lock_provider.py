from __future__ import annotations

from contextlib import contextmanager
from threading import Lock
from typing import TYPE_CHECKING

from payments_core.application.ports import LockProvider

if TYPE_CHECKING:
    from collections.abc import Iterator


class InMemoryLockProvider(LockProvider):
    """In-memory lock provider using per-resource locks.

    Implementation uses two-phase locking:
    1. Global lock protects the lock dictionary during lookup/creation
    2. Resource lock serializes access to the specific resource

    This pattern ensures:
    - No race condition when creating new resource locks
    - Minimal contention (global lock held only briefly)
    - Per-resource parallelism (different resources lock independently)

    Limitations:
    - Single-process only (locks don't work across processes)
    - Unbounded memory growth (locks are never evicted)
    - Not suitable for production with multiple instances
    """

    def __init__(self) -> None:
        self._locks: dict[str, Lock] = {}
        self._global_lock = Lock()

    @contextmanager
    def acquire(self, resource_id: str) -> Iterator[None]:
        # Phase 1: Get or create the resource-specific lock
        # Global lock ensures thread-safe dictionary access
        with self._global_lock:
            if resource_id not in self._locks:
                self._locks[resource_id] = Lock()
            lock = self._locks[resource_id]
        # Global lock is released here - other resources can proceed

        # Phase 2: Acquire the resource-specific lock
        # Using context manager ensures release even on exception
        with lock:
            yield


class NoOpLockProvider(LockProvider):
    """Lock provider that performs no locking.

    Use this for unit tests where:
    - Concurrency is not being tested
    - Tests are single-threaded
    - Lock overhead is unnecessary

    Do NOT use for:
    - Integration tests with concurrent requests
    - Any test verifying race condition handling
    """

    @contextmanager
    def acquire(self, resource_id: str) -> Iterator[None]:  # noqa: ARG002
        yield  # No-op: no lock acquired or released
