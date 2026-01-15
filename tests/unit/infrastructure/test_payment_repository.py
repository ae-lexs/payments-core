"""Tests for InMemoryPaymentRepository based on ADR-004.

Tests cover:
- PaymentRepository interface implementation (ADR-004 Section 2)
- Copy-on-read behavior (ADR-004 Section 5)
- Upsert semantics (ADR-004 Section 2)
- Thread safety is NOT guaranteed (ADR-004 Section 6)
"""

from datetime import UTC, datetime, timedelta

import pytest

from payments_core.application.ports import PaymentRepository
from payments_core.domain.entities import Payment, PaymentState
from payments_core.domain.value_objects import PaymentId
from payments_core.infrastructure.payment_repository import InMemoryPaymentRepository

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def repository() -> InMemoryPaymentRepository:
    return InMemoryPaymentRepository()


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


# =============================================================================
# Interface Tests
# =============================================================================


class TestInMemoryPaymentRepositoryInterface:
    """Test InMemoryPaymentRepository implements PaymentRepository interface."""

    def test_implements_payment_repository_interface(
        self, repository: InMemoryPaymentRepository
    ) -> None:
        assert isinstance(repository, PaymentRepository)


# =============================================================================
# Get Tests - ADR-004 Section 2
# =============================================================================


class TestInMemoryPaymentRepositoryGet:
    """Test get() behavior per ADR-004 Section 2."""

    def test_get_returns_none_for_nonexistent_payment(
        self, repository: InMemoryPaymentRepository, payment_id: PaymentId
    ) -> None:
        """get() returns None if payment does not exist (no exception)."""
        result = repository.get(payment_id)

        assert result is None

    def test_get_returns_saved_payment(
        self, repository: InMemoryPaymentRepository, pending_payment: Payment
    ) -> None:
        repository.save(pending_payment)

        result = repository.get(pending_payment.id)

        assert result is not None
        assert result.id == pending_payment.id
        assert result.state == pending_payment.state

    def test_get_returns_payment_with_all_fields(
        self, repository: InMemoryPaymentRepository, authorized_payment: Payment
    ) -> None:
        repository.save(authorized_payment)

        result = repository.get(authorized_payment.id)

        assert result is not None
        assert result.id == authorized_payment.id
        assert result.state == authorized_payment.state
        assert result.authorized_at == authorized_payment.authorized_at
        assert result.capture_expires_at == authorized_payment.capture_expires_at
        assert result.captured_at == authorized_payment.captured_at
        assert result.captured_amount_cents == authorized_payment.captured_amount_cents


# =============================================================================
# Save Tests - ADR-004 Section 2
# =============================================================================


class TestInMemoryPaymentRepositorySave:
    """Test save() behavior per ADR-004 Section 2."""

    def test_save_creates_new_payment(
        self, repository: InMemoryPaymentRepository, pending_payment: Payment
    ) -> None:
        repository.save(pending_payment)

        result = repository.get(pending_payment.id)
        assert result is not None
        assert result.id == pending_payment.id

    def test_save_updates_existing_payment(
        self,
        repository: InMemoryPaymentRepository,
        pending_payment: Payment,
        now: datetime,
    ) -> None:
        """save() performs upsert: updates if exists."""
        repository.save(pending_payment)

        # Authorize the payment (creates new instance due to frozen dataclass)
        authorized = pending_payment.authorize(now, timedelta(hours=24))
        repository.save(authorized)

        result = repository.get(pending_payment.id)
        assert result is not None
        assert result.state == PaymentState.AUTHORIZED
        assert result.authorized_at == now

    def test_save_multiple_payments(
        self, repository: InMemoryPaymentRepository, now: datetime
    ) -> None:
        payment_1 = Payment(
            id=PaymentId.generate(),
            state=PaymentState.PENDING,
            authorized_at=None,
            capture_expires_at=None,
            captured_at=None,
            captured_amount_cents=None,
        )
        payment_2 = Payment(
            id=PaymentId.generate(),
            state=PaymentState.AUTHORIZED,
            authorized_at=now,
            capture_expires_at=now + timedelta(hours=24),
            captured_at=None,
            captured_amount_cents=None,
        )

        repository.save(payment_1)
        repository.save(payment_2)

        result_1 = repository.get(payment_1.id)
        result_2 = repository.get(payment_2.id)

        assert result_1 is not None
        assert result_2 is not None
        assert result_1.id == payment_1.id
        assert result_2.id == payment_2.id


# =============================================================================
# Copy-on-Read Tests - ADR-004 Section 5
# =============================================================================


class TestInMemoryPaymentRepositoryCopyOnRead:
    """Test copy-on-read behavior per ADR-004 Section 5.

    Returning copies catches bugs where code mutates an entity without
    calling save(). This mimics ORM behavior where fetched entities are
    detached from the session until explicitly merged/committed.
    """

    def test_get_returns_copy_not_original(
        self, repository: InMemoryPaymentRepository, pending_payment: Payment
    ) -> None:
        """Returned entity is a copy; mutations do not affect stored state."""
        repository.save(pending_payment)

        fetched = repository.get(pending_payment.id)

        assert fetched is not pending_payment

    def test_mutating_fetched_entity_does_not_affect_stored(
        self,
        repository: InMemoryPaymentRepository,
        pending_payment: Payment,
    ) -> None:
        """Mutations to fetched entity do not affect stored state.

        Note: Since Payment is a frozen dataclass, we can't directly mutate it.
        Instead, we verify that multiple gets return independent copies.
        """
        repository.save(pending_payment)

        fetched_1 = repository.get(pending_payment.id)
        fetched_2 = repository.get(pending_payment.id)

        # Both fetches return equal but distinct objects
        assert fetched_1 == fetched_2
        assert fetched_1 is not fetched_2

    def test_save_stores_copy_not_reference(
        self, repository: InMemoryPaymentRepository, pending_payment: Payment
    ) -> None:
        """save() stores a copy to prevent external mutation."""
        repository.save(pending_payment)

        # Get the stored payment
        fetched = repository.get(pending_payment.id)

        # Original and fetched should be equal but not the same object
        assert fetched == pending_payment
        assert fetched is not pending_payment

    def test_successive_gets_return_independent_copies(
        self, repository: InMemoryPaymentRepository, authorized_payment: Payment
    ) -> None:
        repository.save(authorized_payment)

        copy_1 = repository.get(authorized_payment.id)
        copy_2 = repository.get(authorized_payment.id)
        copy_3 = repository.get(authorized_payment.id)

        # All copies are equal
        assert copy_1 == copy_2 == copy_3

        # But all are distinct objects
        assert copy_1 is not copy_2
        assert copy_2 is not copy_3
        assert copy_1 is not copy_3


# =============================================================================
# State Transition Tests
# =============================================================================


class TestInMemoryPaymentRepositoryStateTransitions:
    """Test repository correctly persists state transitions."""

    def test_persist_authorization(
        self, repository: InMemoryPaymentRepository, pending_payment: Payment, now: datetime
    ) -> None:
        repository.save(pending_payment)

        authorized = pending_payment.authorize(now, timedelta(hours=24))
        repository.save(authorized)

        result = repository.get(pending_payment.id)
        assert result is not None
        assert result.state == PaymentState.AUTHORIZED

    def test_persist_capture(
        self, repository: InMemoryPaymentRepository, authorized_payment: Payment, now: datetime
    ) -> None:
        repository.save(authorized_payment)

        captured = authorized_payment.capture(now, 5000)
        repository.save(captured)

        result = repository.get(authorized_payment.id)
        assert result is not None
        assert result.state == PaymentState.CAPTURED
        assert result.captured_at == now
        assert result.captured_amount_cents == 5000

    def test_persist_failure(
        self, repository: InMemoryPaymentRepository, authorized_payment: Payment
    ) -> None:
        repository.save(authorized_payment)

        failed = authorized_payment.fail()
        repository.save(failed)

        result = repository.get(authorized_payment.id)
        assert result is not None
        assert result.state == PaymentState.FAILED


# =============================================================================
# Edge Cases
# =============================================================================


class TestInMemoryPaymentRepositoryEdgeCases:
    """Test edge cases."""

    def test_get_with_different_payment_id_instance(
        self, repository: InMemoryPaymentRepository, pending_payment: Payment
    ) -> None:
        """PaymentId equality is by value, not identity."""
        repository.save(pending_payment)

        # Create a new PaymentId instance with the same UUID
        same_id = PaymentId.from_string(str(pending_payment.id.value))

        result = repository.get(same_id)

        assert result is not None
        assert result.id == pending_payment.id

    def test_overwrite_payment_replaces_completely(
        self, repository: InMemoryPaymentRepository, payment_id: PaymentId, now: datetime
    ) -> None:
        """Saving a payment with same ID completely replaces the previous."""
        original = Payment(
            id=payment_id,
            state=PaymentState.PENDING,
            authorized_at=None,
            capture_expires_at=None,
            captured_at=None,
            captured_amount_cents=None,
        )
        repository.save(original)

        replacement = Payment(
            id=payment_id,
            state=PaymentState.CAPTURED,
            authorized_at=now - timedelta(hours=2),
            capture_expires_at=now + timedelta(hours=22),
            captured_at=now,
            captured_amount_cents=9999,
        )
        repository.save(replacement)

        result = repository.get(payment_id)
        assert result is not None
        assert result.state == PaymentState.CAPTURED
        assert result.captured_amount_cents == 9999
