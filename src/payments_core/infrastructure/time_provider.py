from datetime import UTC, datetime

from payments_core.application.ports import TimeProvider


class SystemTimeProvider(TimeProvider):
    """Production time provider using system clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedTimeProvider(TimeProvider):
    """Test time provider with controllable fixed timestamp.

    Note: This implementation is NOT thread-safe. For Stage 1,
    it is intended for single-threaded unit tests only.
    """

    def __init__(self, fixed_time: datetime) -> None:
        self._validate_utc(fixed_time)
        self._fixed_time = fixed_time

    def now(self) -> datetime:
        return self._fixed_time

    def set_time(self, new_time: datetime) -> None:
        """Explicitly change the fixed time for testing scenarios."""
        self._validate_utc(new_time)
        self._fixed_time = new_time

    def _validate_utc(self, dt: datetime) -> None:
        if dt.tzinfo is not UTC:
            raise ValueError(f"datetime must have tzinfo=UTC, got tzinfo={dt.tzinfo}")
