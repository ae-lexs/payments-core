"""Tests for TimeProvider implementations based on ADR-002.

Tests cover:
- SystemTimeProvider returns UTC datetime (ADR-002 Section 3)
- FixedTimeProvider returns fixed time and supports set_time() (ADR-002 Section 5)
- UTC validation rejects non-UTC datetimes (ADR-002 Section 6)
"""

from datetime import UTC, datetime, timezone

import pytest

from payments_core.application.ports import TimeProvider
from payments_core.infrastructure.time_provider import (
    FixedTimeProvider,
    SystemTimeProvider,
)

# =============================================================================
# SystemTimeProvider Tests - ADR-002 Section 3
# =============================================================================


class TestSystemTimeProvider:
    """Test SystemTimeProvider returns UTC datetime."""

    def test_implements_time_provider_interface(self) -> None:
        provider = SystemTimeProvider()

        assert isinstance(provider, TimeProvider)

    def test_now_returns_datetime(self) -> None:
        provider = SystemTimeProvider()

        result = provider.now()

        assert isinstance(result, datetime)

    def test_now_returns_utc_datetime(self) -> None:
        provider = SystemTimeProvider()

        result = provider.now()

        assert result.tzinfo is UTC

    def test_now_returns_current_time(self) -> None:
        provider = SystemTimeProvider()
        before = datetime.now(UTC)

        result = provider.now()

        after = datetime.now(UTC)
        assert before <= result <= after

    def test_successive_calls_return_increasing_time(self) -> None:
        provider = SystemTimeProvider()

        first = provider.now()
        second = provider.now()

        assert second >= first


# =============================================================================
# FixedTimeProvider Creation Tests - ADR-002 Section 5
# =============================================================================


class TestFixedTimeProviderCreation:
    """Test FixedTimeProvider creation and initialization."""

    def test_implements_time_provider_interface(self) -> None:
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        provider = FixedTimeProvider(fixed_time)

        assert isinstance(provider, TimeProvider)

    def test_now_returns_fixed_time(self) -> None:
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        provider = FixedTimeProvider(fixed_time)

        result = provider.now()

        assert result == fixed_time

    def test_now_returns_same_time_on_successive_calls(self) -> None:
        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        provider = FixedTimeProvider(fixed_time)

        first = provider.now()
        second = provider.now()
        third = provider.now()

        assert first == second == third == fixed_time


# =============================================================================
# FixedTimeProvider.set_time() Tests - ADR-002 Section 5
# =============================================================================


class TestFixedTimeProviderSetTime:
    """Test FixedTimeProvider.set_time() for test scenarios."""

    def test_set_time_changes_returned_time(self) -> None:
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        new_time = datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC)
        provider = FixedTimeProvider(initial_time)

        provider.set_time(new_time)

        assert provider.now() == new_time

    def test_set_time_can_move_time_backwards(self) -> None:
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        earlier_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
        provider = FixedTimeProvider(initial_time)

        provider.set_time(earlier_time)

        assert provider.now() == earlier_time

    def test_set_time_can_be_called_multiple_times(self) -> None:
        provider = FixedTimeProvider(datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC))

        provider.set_time(datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC))
        provider.set_time(datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC))
        provider.set_time(datetime(2024, 1, 1, 15, 0, 0, tzinfo=UTC))

        assert provider.now() == datetime(2024, 1, 1, 15, 0, 0, tzinfo=UTC)


# =============================================================================
# UTC Validation Tests - ADR-002 Section 6
# =============================================================================


class TestFixedTimeProviderUtcValidation:
    """Test UTC validation per ADR-002 Section 6.

    FixedTimeProvider validates that input datetimes have tzinfo=UTC specifically,
    not just any timezone-aware value. This is contract enforcement.
    """

    def test_creation_raises_for_naive_datetime(self) -> None:
        naive_datetime = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(ValueError, match="tzinfo=UTC"):
            FixedTimeProvider(naive_datetime)

    def test_creation_raises_for_non_utc_timezone(self) -> None:
        # Create datetime with explicit offset (not UTC)
        offset_tz = timezone(offset=(datetime(1, 1, 1, 6) - datetime(1, 1, 1)))
        non_utc_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=offset_tz)

        with pytest.raises(ValueError, match="tzinfo=UTC"):
            FixedTimeProvider(non_utc_datetime)

    def test_set_time_raises_for_naive_datetime(self) -> None:
        provider = FixedTimeProvider(datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC))
        naive_datetime = datetime(2024, 1, 1, 13, 0, 0)

        with pytest.raises(ValueError, match="tzinfo=UTC"):
            provider.set_time(naive_datetime)

    def test_set_time_raises_for_non_utc_timezone(self) -> None:
        provider = FixedTimeProvider(datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC))
        # Create datetime with explicit offset (not UTC)
        offset_tz = timezone(offset=(datetime(1, 1, 1, 6) - datetime(1, 1, 1)))
        non_utc_datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=offset_tz)

        with pytest.raises(ValueError, match="tzinfo=UTC"):
            provider.set_time(non_utc_datetime)


# =============================================================================
# Edge Cases
# =============================================================================


class TestFixedTimeProviderEdgeCases:
    """Test edge cases for FixedTimeProvider."""

    def test_accepts_datetime_with_microseconds(self) -> None:
        precise_time = datetime(2024, 1, 1, 12, 0, 0, 123456, tzinfo=UTC)
        provider = FixedTimeProvider(precise_time)

        assert provider.now() == precise_time
        assert provider.now().microsecond == 123456

    def test_accepts_min_datetime(self) -> None:
        min_time = datetime.min.replace(tzinfo=UTC)
        provider = FixedTimeProvider(min_time)

        assert provider.now() == min_time

    def test_accepts_max_datetime(self) -> None:
        max_time = datetime.max.replace(tzinfo=UTC)
        provider = FixedTimeProvider(max_time)

        assert provider.now() == max_time
