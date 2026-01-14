"""Tests for Payment entity based on ADR-001.

Tests cover:
- Payment state machine (ADR-001 Section 2)
- State transitions: pending → authorized → captured, authorized → failed
- Invalid transitions raising InvalidStateTransitionError
- Terminal state immutability (ADR-001 Section 6.2)
- Capture window enforcement via can_capture() (ADR-001 Section 6.3)
- Expiry policy: payment stays AUTHORIZED but capture rejected after expiry
"""

from datetime import UTC, datetime, timedelta

import pytest

from payments_core.domain.entities.payment import Payment, PaymentState
from payments_core.domain.exceptions import InvalidStateTransitionError
from payments_core.domain.value_objects import PaymentId

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def payment_id() -> PaymentId:
    return PaymentId.generate()


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def pending_payment(payment_id: PaymentId) -> Payment:
    return Payment(
        id=payment_id,
        state=PaymentState.PENDING,
        authorized_at=None,
        capture_expires_at=None,
        captured_at=None,
        captured_amount_cents=None,
    )


@pytest.fixture
def authorized_payment(payment_id: PaymentId, now: datetime) -> Payment:
    return Payment(
        id=payment_id,
        state=PaymentState.AUTHORIZED,
        authorized_at=now - timedelta(hours=1),
        capture_expires_at=now + timedelta(hours=23),
        captured_at=None,
        captured_amount_cents=None,
    )


@pytest.fixture
def captured_payment(payment_id: PaymentId, now: datetime) -> Payment:
    return Payment(
        id=payment_id,
        state=PaymentState.CAPTURED,
        authorized_at=now - timedelta(hours=2),
        capture_expires_at=now + timedelta(hours=22),
        captured_at=now - timedelta(hours=1),
        captured_amount_cents=1000,
    )


@pytest.fixture
def failed_payment(payment_id: PaymentId, now: datetime) -> Payment:
    return Payment(
        id=payment_id,
        state=PaymentState.FAILED,
        authorized_at=now - timedelta(hours=1),
        capture_expires_at=now + timedelta(hours=23),
        captured_at=None,
        captured_amount_cents=None,
    )


@pytest.fixture
def expired_payment(payment_id: PaymentId, now: datetime) -> Payment:
    """An authorized payment whose capture window has expired."""
    return Payment(
        id=payment_id,
        state=PaymentState.AUTHORIZED,
        authorized_at=now - timedelta(hours=25),
        capture_expires_at=now - timedelta(hours=1),
        captured_at=None,
        captured_amount_cents=None,
    )


# =============================================================================
# PaymentState Enum Tests
# =============================================================================


class TestPaymentState:
    """Test PaymentState enum values per ADR-001 Section 2."""

    def test_pending_state_value(self) -> None:
        assert PaymentState.PENDING.value == "pending"

    def test_authorized_state_value(self) -> None:
        assert PaymentState.AUTHORIZED.value == "authorized"

    def test_captured_state_value(self) -> None:
        assert PaymentState.CAPTURED.value == "captured"

    def test_failed_state_value(self) -> None:
        assert PaymentState.FAILED.value == "failed"

    def test_all_states_exist(self) -> None:
        states = {s.value for s in PaymentState}
        assert states == {"pending", "authorized", "captured", "failed"}


# =============================================================================
# Payment Creation Tests
# =============================================================================


class TestPaymentCreation:
    """Test Payment entity creation and immutability."""

    def test_create_pending_payment(self, pending_payment: Payment) -> None:
        assert pending_payment.state == PaymentState.PENDING
        assert pending_payment.authorized_at is None
        assert pending_payment.capture_expires_at is None
        assert pending_payment.captured_at is None
        assert pending_payment.captured_amount_cents is None

    def test_payment_is_frozen_dataclass(self, pending_payment: Payment) -> None:
        with pytest.raises(AttributeError):
            pending_payment.state = PaymentState.AUTHORIZED  # type: ignore[misc]


# =============================================================================
# Payment.authorize() Tests - ADR-001 Section 2
# =============================================================================


class TestPaymentAuthorize:
    """Test Payment.authorize() transition.

    Valid transition: pending → authorized (ADR-001 Section 2)
    """

    def test_authorize_pending_payment_succeeds(
        self, pending_payment: Payment, now: datetime
    ) -> None:
        capture_window = timedelta(hours=24)

        authorized = pending_payment.authorize(now, capture_window)

        assert authorized.state == PaymentState.AUTHORIZED
        assert authorized.authorized_at == now
        assert authorized.capture_expires_at == now + capture_window

    def test_authorize_returns_new_instance(self, pending_payment: Payment, now: datetime) -> None:
        """Payment is immutable; authorize() returns a new instance."""
        authorized = pending_payment.authorize(now, timedelta(hours=24))

        assert authorized is not pending_payment
        assert pending_payment.state == PaymentState.PENDING

    def test_authorize_preserves_payment_id(self, pending_payment: Payment, now: datetime) -> None:
        authorized = pending_payment.authorize(now, timedelta(hours=24))

        assert authorized.id == pending_payment.id

    def test_authorize_authorized_payment_raises(
        self, authorized_payment: Payment, now: datetime
    ) -> None:
        with pytest.raises(InvalidStateTransitionError):
            authorized_payment.authorize(now, timedelta(hours=24))

    def test_authorize_captured_payment_raises(
        self, captured_payment: Payment, now: datetime
    ) -> None:
        with pytest.raises(InvalidStateTransitionError):
            captured_payment.authorize(now, timedelta(hours=24))

    def test_authorize_failed_payment_raises(self, failed_payment: Payment, now: datetime) -> None:
        with pytest.raises(InvalidStateTransitionError):
            failed_payment.authorize(now, timedelta(hours=24))


# =============================================================================
# Payment.can_capture() Tests - ADR-001 Section 6.3
# =============================================================================


class TestPaymentCanCapture:
    """Test Payment.can_capture() per ADR-001 Section 6.3.

    Capture window enforcement: capture only succeeds if now < capture_expires_at
    """

    def test_can_capture_authorized_before_expiry(
        self, authorized_payment: Payment, now: datetime
    ) -> None:
        assert authorized_payment.can_capture(now) is True

    def test_cannot_capture_at_exact_expiry(self, payment_id: PaymentId, now: datetime) -> None:
        """Capture rejected when now == capture_expires_at (strict less-than)."""
        payment = Payment(
            id=payment_id,
            state=PaymentState.AUTHORIZED,
            authorized_at=now - timedelta(hours=24),
            capture_expires_at=now,
            captured_at=None,
            captured_amount_cents=None,
        )

        assert payment.can_capture(now) is False

    def test_cannot_capture_after_expiry(self, expired_payment: Payment, now: datetime) -> None:
        assert expired_payment.can_capture(now) is False

    def test_cannot_capture_pending_payment(self, pending_payment: Payment, now: datetime) -> None:
        assert pending_payment.can_capture(now) is False

    def test_cannot_capture_captured_payment(
        self, captured_payment: Payment, now: datetime
    ) -> None:
        assert captured_payment.can_capture(now) is False

    def test_cannot_capture_failed_payment(self, failed_payment: Payment, now: datetime) -> None:
        assert failed_payment.can_capture(now) is False

    def test_can_capture_one_microsecond_before_expiry(
        self, payment_id: PaymentId, now: datetime
    ) -> None:
        """Edge case: capture allowed 1 microsecond before expiry."""
        expiry = now + timedelta(microseconds=1)
        payment = Payment(
            id=payment_id,
            state=PaymentState.AUTHORIZED,
            authorized_at=now - timedelta(hours=1),
            capture_expires_at=expiry,
            captured_at=None,
            captured_amount_cents=None,
        )

        assert payment.can_capture(now) is True


# =============================================================================
# Payment.capture() Tests - ADR-001 Section 2
# =============================================================================


class TestPaymentCapture:
    """Test Payment.capture() transition.

    Valid transition: authorized → captured (ADR-001 Section 2)
    """

    def test_capture_authorized_payment_succeeds(
        self, authorized_payment: Payment, now: datetime
    ) -> None:
        amount_cents = 5000

        captured = authorized_payment.capture(now, amount_cents)

        assert captured.state == PaymentState.CAPTURED
        assert captured.captured_at == now
        assert captured.captured_amount_cents == amount_cents

    def test_capture_returns_new_instance(self, authorized_payment: Payment, now: datetime) -> None:
        """Payment is immutable; capture() returns a new instance."""
        captured = authorized_payment.capture(now, 5000)

        assert captured is not authorized_payment
        assert authorized_payment.state == PaymentState.AUTHORIZED

    def test_capture_preserves_authorization_fields(
        self, authorized_payment: Payment, now: datetime
    ) -> None:
        captured = authorized_payment.capture(now, 5000)

        assert captured.id == authorized_payment.id
        assert captured.authorized_at == authorized_payment.authorized_at
        assert captured.capture_expires_at == authorized_payment.capture_expires_at

    def test_capture_pending_payment_raises(self, pending_payment: Payment, now: datetime) -> None:
        with pytest.raises(InvalidStateTransitionError):
            pending_payment.capture(now, 5000)

    def test_capture_captured_payment_raises(
        self, captured_payment: Payment, now: datetime
    ) -> None:
        with pytest.raises(InvalidStateTransitionError):
            captured_payment.capture(now, 5000)

    def test_capture_failed_payment_raises(self, failed_payment: Payment, now: datetime) -> None:
        with pytest.raises(InvalidStateTransitionError):
            failed_payment.capture(now, 5000)


# =============================================================================
# Payment.fail() Tests - ADR-001 Section 2
# =============================================================================


class TestPaymentFail:
    """Test Payment.fail() transition.

    Valid transition: authorized → failed (ADR-001 Section 2)
    """

    def test_fail_authorized_payment_succeeds(self, authorized_payment: Payment) -> None:
        failed = authorized_payment.fail()

        assert failed.state == PaymentState.FAILED

    def test_fail_returns_new_instance(self, authorized_payment: Payment) -> None:
        """Payment is immutable; fail() returns a new instance."""
        failed = authorized_payment.fail()

        assert failed is not authorized_payment
        assert authorized_payment.state == PaymentState.AUTHORIZED

    def test_fail_preserves_fields(self, authorized_payment: Payment) -> None:
        failed = authorized_payment.fail()

        assert failed.id == authorized_payment.id
        assert failed.authorized_at == authorized_payment.authorized_at
        assert failed.capture_expires_at == authorized_payment.capture_expires_at

    def test_fail_pending_payment_raises(self, pending_payment: Payment) -> None:
        with pytest.raises(InvalidStateTransitionError):
            pending_payment.fail()

    def test_fail_captured_payment_raises(self, captured_payment: Payment) -> None:
        with pytest.raises(InvalidStateTransitionError):
            captured_payment.fail()

    def test_fail_already_failed_payment_raises(self, failed_payment: Payment) -> None:
        with pytest.raises(InvalidStateTransitionError):
            failed_payment.fail()


# =============================================================================
# Expiry Policy Tests - ADR-001 Section 2
# =============================================================================


class TestPaymentExpiryPolicy:
    """Test expiry policy per ADR-001 Section 2.

    Window expiration does NOT auto-transition the payment.
    Payment remains AUTHORIZED but can_capture() returns False.
    """

    def test_expired_payment_remains_authorized(self, expired_payment: Payment) -> None:
        """Payment stays in AUTHORIZED state even after capture window expires."""
        assert expired_payment.state == PaymentState.AUTHORIZED

    def test_expired_payment_cannot_be_captured(
        self, expired_payment: Payment, now: datetime
    ) -> None:
        """can_capture() returns False for expired payments."""
        assert expired_payment.can_capture(now) is False


# =============================================================================
# Terminal State Tests - ADR-001 Section 6.2
# =============================================================================


class TestPaymentTerminalState:
    """Test terminal state immutability per ADR-001 Section 6.2.

    CAPTURED is a terminal state—no further transitions allowed.
    """

    def test_captured_payment_cannot_authorize(
        self, captured_payment: Payment, now: datetime
    ) -> None:
        with pytest.raises(InvalidStateTransitionError):
            captured_payment.authorize(now, timedelta(hours=24))

    def test_captured_payment_cannot_capture_again(
        self, captured_payment: Payment, now: datetime
    ) -> None:
        with pytest.raises(InvalidStateTransitionError):
            captured_payment.capture(now, 5000)

    def test_captured_payment_cannot_fail(self, captured_payment: Payment) -> None:
        with pytest.raises(InvalidStateTransitionError):
            captured_payment.fail()
