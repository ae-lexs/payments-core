"""Shared pytest fixtures for the test suite."""

from datetime import UTC, datetime

import pytest

from payments_core.infrastructure.locking import InMemoryLockProvider
from payments_core.infrastructure.time_provider import FixedTimeProvider


@pytest.fixture
def fixed_time() -> datetime:
    """A fixed timestamp for deterministic testing."""
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def time_provider(fixed_time: datetime) -> FixedTimeProvider:
    """A time provider with a fixed timestamp."""
    return FixedTimeProvider(fixed_time)


@pytest.fixture
def lock_provider() -> InMemoryLockProvider:
    """An in-memory lock provider for testing."""
    return InMemoryLockProvider()
