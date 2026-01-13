"""Shared pytest fixtures for the test suite."""

import pytest
from datetime import datetime, timezone

from payments_core.infrastructure.time_provider import FixedTimeProvider
from payments_core.infrastructure.locking import InMemoryLockProvider


@pytest.fixture
def fixed_time() -> datetime:
    """A fixed timestamp for deterministic testing."""
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def time_provider(fixed_time: datetime) -> FixedTimeProvider:
    """A time provider with a fixed timestamp."""
    return FixedTimeProvider(fixed_time)


@pytest.fixture
def lock_provider() -> InMemoryLockProvider:
    """An in-memory lock provider for testing."""
    return InMemoryLockProvider()
