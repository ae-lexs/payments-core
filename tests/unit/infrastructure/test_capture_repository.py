"""Tests for InMemoryCaptureRepository based on ADR-004.

Tests cover:
- CaptureRepository interface implementation (ADR-004 Section 3)
- Copy-on-read behavior (ADR-004 Section 5)
- DuplicateCaptureError on duplicate (payment_id, idempotency_key) (ADR-004 Section 3)
- Idempotency key scoped to specific payment
"""

from datetime import UTC, datetime

import pytest

from payments_core.application.ports import CaptureRepository
from payments_core.domain.entities import Capture
from payments_core.domain.exceptions import DuplicateCaptureError
from payments_core.domain.value_objects import CaptureId, IdempotencyKey, PaymentId
from payments_core.infrastructure.capture_repository import InMemoryCaptureRepository

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def repository() -> InMemoryCaptureRepository:
    return InMemoryCaptureRepository()


@pytest.fixture
def payment_id() -> PaymentId:
    return PaymentId.generate()


@pytest.fixture
def idempotency_key() -> IdempotencyKey:
    return IdempotencyKey(value="test-idempotency-key")


@pytest.fixture
def now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def capture(payment_id: PaymentId, idempotency_key: IdempotencyKey, now: datetime) -> Capture:
    return Capture(
        id=CaptureId.generate(),
        payment_id=payment_id,
        idempotency_key=idempotency_key,
        amount_cents=1000,
        created_at=now,
    )


# =============================================================================
# Interface Tests
# =============================================================================


class TestInMemoryCaptureRepositoryInterface:
    """Test InMemoryCaptureRepository implements CaptureRepository interface."""

    def test_implements_capture_repository_interface(
        self, repository: InMemoryCaptureRepository
    ) -> None:
        assert isinstance(repository, CaptureRepository)


# =============================================================================
# Get By Idempotency Key Tests - ADR-004 Section 3
# =============================================================================


class TestInMemoryCaptureRepositoryGetByIdempotencyKey:
    """Test get_by_idempotency_key() behavior per ADR-004 Section 3."""

    def test_returns_none_for_nonexistent_capture(
        self,
        repository: InMemoryCaptureRepository,
        payment_id: PaymentId,
        idempotency_key: IdempotencyKey,
    ) -> None:
        result = repository.get_by_idempotency_key(payment_id, idempotency_key)

        assert result is None

    def test_returns_saved_capture(
        self, repository: InMemoryCaptureRepository, capture: Capture
    ) -> None:
        repository.save(capture)

        result = repository.get_by_idempotency_key(capture.payment_id, capture.idempotency_key)

        assert result is not None
        assert result.id == capture.id
        assert result.payment_id == capture.payment_id
        assert result.idempotency_key == capture.idempotency_key
        assert result.amount_cents == capture.amount_cents
        assert result.created_at == capture.created_at

    def test_returns_none_for_different_payment_id(
        self, repository: InMemoryCaptureRepository, capture: Capture
    ) -> None:
        """Idempotency key is scoped to a specific payment."""
        repository.save(capture)

        different_payment_id = PaymentId.generate()
        result = repository.get_by_idempotency_key(different_payment_id, capture.idempotency_key)

        assert result is None

    def test_returns_none_for_different_idempotency_key(
        self, repository: InMemoryCaptureRepository, capture: Capture
    ) -> None:
        repository.save(capture)

        different_key = IdempotencyKey(value="different-key")
        result = repository.get_by_idempotency_key(capture.payment_id, different_key)

        assert result is None


# =============================================================================
# Save Tests - ADR-004 Section 3
# =============================================================================


class TestInMemoryCaptureRepositorySave:
    """Test save() behavior per ADR-004 Section 3."""

    def test_save_creates_new_capture(
        self, repository: InMemoryCaptureRepository, capture: Capture
    ) -> None:
        repository.save(capture)

        result = repository.get_by_idempotency_key(capture.payment_id, capture.idempotency_key)
        assert result is not None
        assert result.id == capture.id

    def test_save_raises_duplicate_capture_error_on_duplicate(
        self, repository: InMemoryCaptureRepository, capture: Capture, now: datetime
    ) -> None:
        """DuplicateCaptureError if (payment_id, idempotency_key) already exists."""
        repository.save(capture)

        # Create a different capture with same (payment_id, idempotency_key)
        duplicate = Capture(
            id=CaptureId.generate(),
            payment_id=capture.payment_id,
            idempotency_key=capture.idempotency_key,
            amount_cents=2000,  # Different amount
            created_at=now,
        )

        with pytest.raises(DuplicateCaptureError):
            repository.save(duplicate)

    def test_save_allows_same_idempotency_key_for_different_payments(
        self, repository: InMemoryCaptureRepository, idempotency_key: IdempotencyKey, now: datetime
    ) -> None:
        """Same idempotency key can be used for different payments."""
        capture_1 = Capture(
            id=CaptureId.generate(),
            payment_id=PaymentId.generate(),
            idempotency_key=idempotency_key,
            amount_cents=1000,
            created_at=now,
        )
        capture_2 = Capture(
            id=CaptureId.generate(),
            payment_id=PaymentId.generate(),
            idempotency_key=idempotency_key,
            amount_cents=2000,
            created_at=now,
        )

        repository.save(capture_1)
        repository.save(capture_2)  # Should not raise

        result_1 = repository.get_by_idempotency_key(capture_1.payment_id, idempotency_key)
        result_2 = repository.get_by_idempotency_key(capture_2.payment_id, idempotency_key)

        assert result_1 is not None
        assert result_2 is not None
        assert result_1.id == capture_1.id
        assert result_2.id == capture_2.id

    def test_save_allows_different_idempotency_keys_for_same_payment(
        self, repository: InMemoryCaptureRepository, payment_id: PaymentId, now: datetime
    ) -> None:
        """Different idempotency keys can be used for the same payment.

        Note: In practice, only one capture should succeed per payment
        (use case enforces this), but the repository allows it.
        """
        capture_1 = Capture(
            id=CaptureId.generate(),
            payment_id=payment_id,
            idempotency_key=IdempotencyKey(value="key-1"),
            amount_cents=1000,
            created_at=now,
        )
        capture_2 = Capture(
            id=CaptureId.generate(),
            payment_id=payment_id,
            idempotency_key=IdempotencyKey(value="key-2"),
            amount_cents=2000,
            created_at=now,
        )

        repository.save(capture_1)
        repository.save(capture_2)  # Should not raise

        result_1 = repository.get_by_idempotency_key(payment_id, IdempotencyKey(value="key-1"))
        result_2 = repository.get_by_idempotency_key(payment_id, IdempotencyKey(value="key-2"))

        assert result_1 is not None
        assert result_2 is not None


# =============================================================================
# Copy-on-Read Tests - ADR-004 Section 5
# =============================================================================


class TestInMemoryCaptureRepositoryCopyOnRead:
    """Test copy-on-read behavior per ADR-004 Section 5."""

    def test_get_returns_copy_not_original(
        self, repository: InMemoryCaptureRepository, capture: Capture
    ) -> None:
        """Returned entity is a copy; mutations do not affect stored state."""
        repository.save(capture)

        fetched = repository.get_by_idempotency_key(capture.payment_id, capture.idempotency_key)

        assert fetched is not capture

    def test_successive_gets_return_independent_copies(
        self, repository: InMemoryCaptureRepository, capture: Capture
    ) -> None:
        repository.save(capture)

        copy_1 = repository.get_by_idempotency_key(capture.payment_id, capture.idempotency_key)
        copy_2 = repository.get_by_idempotency_key(capture.payment_id, capture.idempotency_key)
        copy_3 = repository.get_by_idempotency_key(capture.payment_id, capture.idempotency_key)

        # All copies are equal
        assert copy_1 == copy_2 == copy_3

        # But all are distinct objects
        assert copy_1 is not copy_2
        assert copy_2 is not copy_3
        assert copy_1 is not copy_3

    def test_save_stores_copy_not_reference(
        self, repository: InMemoryCaptureRepository, capture: Capture
    ) -> None:
        """save() stores a copy to prevent external mutation."""
        repository.save(capture)

        fetched = repository.get_by_idempotency_key(capture.payment_id, capture.idempotency_key)

        # Original and fetched should be equal but not the same object
        assert fetched == capture
        assert fetched is not capture


# =============================================================================
# Edge Cases
# =============================================================================


class TestInMemoryCaptureRepositoryEdgeCases:
    """Test edge cases."""

    def test_get_with_equivalent_value_objects(
        self, repository: InMemoryCaptureRepository, capture: Capture
    ) -> None:
        """Value object equality is by value, not identity."""
        repository.save(capture)

        # Create new instances with the same values
        same_payment_id = PaymentId.from_string(str(capture.payment_id.value))
        same_idempotency_key = IdempotencyKey(value=capture.idempotency_key.value)

        result = repository.get_by_idempotency_key(same_payment_id, same_idempotency_key)

        assert result is not None
        assert result.id == capture.id

    def test_multiple_captures_stored_independently(
        self, repository: InMemoryCaptureRepository, now: datetime
    ) -> None:
        captures = [
            Capture(
                id=CaptureId.generate(),
                payment_id=PaymentId.generate(),
                idempotency_key=IdempotencyKey(value=f"key-{i}"),
                amount_cents=1000 * (i + 1),
                created_at=now,
            )
            for i in range(5)
        ]

        for c in captures:
            repository.save(c)

        for c in captures:
            result = repository.get_by_idempotency_key(c.payment_id, c.idempotency_key)
            assert result is not None
            assert result.id == c.id
            assert result.amount_cents == c.amount_cents

    def test_duplicate_error_message_contains_details(
        self, repository: InMemoryCaptureRepository, capture: Capture, now: datetime
    ) -> None:
        repository.save(capture)

        duplicate = Capture(
            id=CaptureId.generate(),
            payment_id=capture.payment_id,
            idempotency_key=capture.idempotency_key,
            amount_cents=9999,
            created_at=now,
        )

        with pytest.raises(DuplicateCaptureError) as exc_info:
            repository.save(duplicate)

        error_message = str(exc_info.value)
        assert "payment_id" in error_message
        assert "idempotency_key" in error_message
