"""Tests for Capture entity based on ADR-001.

Tests cover:
- Capture.create() factory method with validation (ADR-001 Section 6.6)
- Amount validation: amount_cents must be > 0
- Capture immutability (frozen dataclass)
"""

from datetime import UTC, datetime

import pytest

from payments_core.domain.entities import Capture
from payments_core.domain.exceptions import InvalidAmountError
from payments_core.domain.value_objects import CaptureId, IdempotencyKey, PaymentId

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def payment_id() -> PaymentId:
    return PaymentId.generate()


@pytest.fixture
def idempotency_key() -> IdempotencyKey:
    return IdempotencyKey(value="request-123")


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


# =============================================================================
# Capture.create() Factory Tests - ADR-001 Section 6.6
# =============================================================================


class TestCaptureCreate:
    """Test Capture.create() factory method.

    Per ADR-001 Section 6.6: amount_cents must be greater than 0.
    """

    def test_create_capture_with_valid_amount(
        self, payment_id: PaymentId, idempotency_key: IdempotencyKey, now: datetime
    ) -> None:
        capture = Capture.create(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
            created_at=now,
        )

        assert capture.payment_id == payment_id
        assert capture.idempotency_key == idempotency_key
        assert capture.amount_cents == 1000
        assert capture.created_at == now

    def test_create_generates_unique_capture_id(
        self, payment_id: PaymentId, idempotency_key: IdempotencyKey, now: datetime
    ) -> None:
        capture = Capture.create(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
            created_at=now,
        )

        assert isinstance(capture.id, CaptureId)

    def test_create_with_minimum_valid_amount(
        self, payment_id: PaymentId, idempotency_key: IdempotencyKey, now: datetime
    ) -> None:
        """amount_cents = 1 is the minimum valid amount."""
        capture = Capture.create(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1,
            created_at=now,
        )

        assert capture.amount_cents == 1

    def test_create_with_large_amount(
        self, payment_id: PaymentId, idempotency_key: IdempotencyKey, now: datetime
    ) -> None:
        """Large amounts should be accepted."""
        large_amount = 100_000_000_00  # $100 million in cents
        capture = Capture.create(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=large_amount,
            created_at=now,
        )

        assert capture.amount_cents == large_amount


class TestCaptureCreateValidation:
    """Test Capture.create() validation.

    Per ADR-001 Section 6.6: amount_cents must be greater than 0.
    """

    def test_create_raises_for_zero_amount(
        self, payment_id: PaymentId, idempotency_key: IdempotencyKey, now: datetime
    ) -> None:
        with pytest.raises(InvalidAmountError):
            Capture.create(
                payment_id=payment_id,
                idempotency_key=idempotency_key,
                amount_cents=0,
                created_at=now,
            )

    def test_create_raises_for_negative_amount(
        self, payment_id: PaymentId, idempotency_key: IdempotencyKey, now: datetime
    ) -> None:
        with pytest.raises(InvalidAmountError):
            Capture.create(
                payment_id=payment_id,
                idempotency_key=idempotency_key,
                amount_cents=-100,
                created_at=now,
            )

    def test_create_raises_for_large_negative_amount(
        self, payment_id: PaymentId, idempotency_key: IdempotencyKey, now: datetime
    ) -> None:
        with pytest.raises(InvalidAmountError):
            Capture.create(
                payment_id=payment_id,
                idempotency_key=idempotency_key,
                amount_cents=-1_000_000,
                created_at=now,
            )


# =============================================================================
# Capture Immutability Tests
# =============================================================================


class TestCaptureImmutability:
    """Test Capture entity immutability."""

    def test_capture_is_frozen_dataclass(
        self, payment_id: PaymentId, idempotency_key: IdempotencyKey, now: datetime
    ) -> None:
        capture = Capture.create(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
            created_at=now,
        )

        with pytest.raises(AttributeError):
            capture.amount_cents = 2000  # type: ignore[misc]


# =============================================================================
# Capture Equality Tests
# =============================================================================


class TestCaptureEquality:
    """Test Capture equality based on all fields."""

    def test_captures_with_same_fields_are_equal(
        self, payment_id: PaymentId, idempotency_key: IdempotencyKey, now: datetime
    ) -> None:
        capture_id = CaptureId.generate()
        capture_1 = Capture(
            id=capture_id,
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
            created_at=now,
        )
        capture_2 = Capture(
            id=capture_id,
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
            created_at=now,
        )

        assert capture_1 == capture_2

    def test_captures_with_different_ids_are_not_equal(
        self, payment_id: PaymentId, idempotency_key: IdempotencyKey, now: datetime
    ) -> None:
        capture_1 = Capture.create(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
            created_at=now,
        )
        capture_2 = Capture.create(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
            created_at=now,
        )

        assert capture_1 != capture_2
