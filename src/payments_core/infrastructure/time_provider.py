"""Time provider - Clock abstraction for testability."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class TimeProvider(ABC):
    """Abstract time provider for clock operations."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current UTC datetime."""


class SystemTimeProvider(TimeProvider):
    """Production time provider using system clock."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedTimeProvider(TimeProvider):
    """Test time provider with a fixed timestamp."""

    def __init__(self, fixed_time: datetime) -> None:
        self._fixed_time = fixed_time

    def now(self) -> datetime:
        return self._fixed_time

    def set_time(self, new_time: datetime) -> None:
        """Update the fixed time (useful for testing time-based scenarios)."""
        self._fixed_time = new_time
