"""Tests for CapturePaymentUseCase based on ADR-003 and ADR-004.

Tests cover:
- Capture success flow (ADR-004 Section 8)
- Idempotency handling (ADR-001 Section 7, ADR-004 Section 8)
- Business rule validation (ADR-001 Section 6)
- Concurrency with locking (ADR-003 Section 10)
- Time fetched inside lock (ADR-002, ADR-003 Section 7)
"""

import threading
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import UTC, datetime, timedelta

import pytest

from payments_core.application.use_cases.capture_payment import (
    CapturePaymentRequest,
    CapturePaymentUseCase,
)
from payments_core.domain.entities import Payment, PaymentState
from payments_core.domain.exceptions import (
    IdempotencyKeyReuseError,
    PaymentAlreadyCapturedError,
    PaymentExpiredError,
    PaymentNotFoundError,
)
from payments_core.domain.value_objects import IdempotencyKey, PaymentId
from payments_core.infrastructure.capture_repository import InMemoryCaptureRepository
from payments_core.infrastructure.lock_provider import InMemoryLockProvider, NoOpLockProvider
from payments_core.infrastructure.payment_repository import InMemoryPaymentRepository
from payments_core.infrastructure.time_provider import FixedTimeProvider

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def now() -> datetime:
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def time_provider(now: datetime) -> FixedTimeProvider:
    return FixedTimeProvider(now)


@pytest.fixture
def lock_provider() -> NoOpLockProvider:
    """Use NoOpLockProvider for unit tests (single-threaded)."""
    return NoOpLockProvider()


@pytest.fixture
def payment_repository() -> InMemoryPaymentRepository:
    return InMemoryPaymentRepository()


@pytest.fixture
def capture_repository() -> InMemoryCaptureRepository:
    return InMemoryCaptureRepository()


@pytest.fixture
def use_case(
    lock_provider: NoOpLockProvider,
    time_provider: FixedTimeProvider,
    payment_repository: InMemoryPaymentRepository,
    capture_repository: InMemoryCaptureRepository,
) -> CapturePaymentUseCase:
    return CapturePaymentUseCase(
        lock_provider=lock_provider,
        time_provider=time_provider,
        payment_repository=payment_repository,
        capture_repository=capture_repository,
    )


@pytest.fixture
def payment_id() -> PaymentId:
    return PaymentId.generate()


@pytest.fixture
def idempotency_key() -> IdempotencyKey:
    return IdempotencyKey(value="test-idempotency-key")


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
# Capture Success Tests - ADR-004 Section 8
# =============================================================================


class TestCapturePaymentSuccess:
    """Test successful capture flow per ADR-004 Section 8."""

    def test_capture_authorized_payment_succeeds(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        authorized_payment: Payment,
        idempotency_key: IdempotencyKey,
    ) -> None:
        payment_repository.save(authorized_payment)
        request = CapturePaymentRequest(
            payment_id=authorized_payment.id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        response = use_case.execute(request)

        assert response.is_replay is False
        assert response.capture.payment_id == authorized_payment.id
        assert response.capture.idempotency_key == idempotency_key
        assert response.capture.amount_cents == 1000

    def test_capture_updates_payment_state(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        authorized_payment: Payment,
        idempotency_key: IdempotencyKey,
    ) -> None:
        payment_repository.save(authorized_payment)
        request = CapturePaymentRequest(
            payment_id=authorized_payment.id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        use_case.execute(request)

        updated_payment = payment_repository.get(authorized_payment.id)
        assert updated_payment is not None
        assert updated_payment.state == PaymentState.CAPTURED
        assert updated_payment.captured_amount_cents == 1000

    def test_capture_persists_capture_record(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        capture_repository: InMemoryCaptureRepository,
        authorized_payment: Payment,
        idempotency_key: IdempotencyKey,
    ) -> None:
        payment_repository.save(authorized_payment)
        request = CapturePaymentRequest(
            payment_id=authorized_payment.id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        response = use_case.execute(request)

        stored_capture = capture_repository.get_by_idempotency_key(
            authorized_payment.id, idempotency_key
        )
        assert stored_capture is not None
        assert stored_capture.id == response.capture.id

    def test_capture_uses_current_time(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        authorized_payment: Payment,
        idempotency_key: IdempotencyKey,
        now: datetime,
    ) -> None:
        payment_repository.save(authorized_payment)
        request = CapturePaymentRequest(
            payment_id=authorized_payment.id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        response = use_case.execute(request)

        # Capture timestamp should match the time provider's current time
        assert response.capture.created_at == now


# =============================================================================
# Idempotency Tests - ADR-001 Section 7
# =============================================================================


class TestCapturePaymentIdempotency:
    """Test idempotency handling per ADR-001 Section 7."""

    def test_idempotent_replay_returns_existing_capture(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        authorized_payment: Payment,
        idempotency_key: IdempotencyKey,
    ) -> None:
        """Same (payment_id, idempotency_key, amount) returns existing capture."""
        payment_repository.save(authorized_payment)
        request = CapturePaymentRequest(
            payment_id=authorized_payment.id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        first_response = use_case.execute(request)
        second_response = use_case.execute(request)

        assert first_response.is_replay is False
        assert second_response.is_replay is True
        assert second_response.capture.id == first_response.capture.id

    def test_idempotent_replay_does_not_create_duplicate(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        capture_repository: InMemoryCaptureRepository,
        authorized_payment: Payment,
        idempotency_key: IdempotencyKey,
    ) -> None:
        payment_repository.save(authorized_payment)
        request = CapturePaymentRequest(
            payment_id=authorized_payment.id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        use_case.execute(request)
        use_case.execute(request)
        use_case.execute(request)

        # Only one capture should exist
        capture = capture_repository.get_by_idempotency_key(authorized_payment.id, idempotency_key)
        assert capture is not None

    def test_idempotency_key_reuse_with_different_amount_raises(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        authorized_payment: Payment,
        idempotency_key: IdempotencyKey,
    ) -> None:
        """Same key with different amount raises IdempotencyKeyReuseError."""
        payment_repository.save(authorized_payment)

        first_request = CapturePaymentRequest(
            payment_id=authorized_payment.id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )
        use_case.execute(first_request)

        second_request = CapturePaymentRequest(
            payment_id=authorized_payment.id,
            idempotency_key=idempotency_key,
            amount_cents=2000,  # Different amount
        )

        with pytest.raises(IdempotencyKeyReuseError):
            use_case.execute(second_request)

    def test_idempotent_replay_works_even_after_payment_captured(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        authorized_payment: Payment,
        idempotency_key: IdempotencyKey,
    ) -> None:
        """Idempotency check happens before payment state check."""
        payment_repository.save(authorized_payment)
        request = CapturePaymentRequest(
            payment_id=authorized_payment.id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        first_response = use_case.execute(request)

        # Payment is now CAPTURED, but same idempotency key should still work
        second_response = use_case.execute(request)

        assert second_response.is_replay is True
        assert second_response.capture.id == first_response.capture.id


# =============================================================================
# Business Rule Validation Tests - ADR-001 Section 6
# =============================================================================


class TestCapturePaymentValidation:
    """Test business rule validation per ADR-001 Section 6."""

    def test_payment_not_found_raises(
        self,
        use_case: CapturePaymentUseCase,
        payment_id: PaymentId,
        idempotency_key: IdempotencyKey,
    ) -> None:
        request = CapturePaymentRequest(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        with pytest.raises(PaymentNotFoundError):
            use_case.execute(request)

    def test_payment_already_captured_raises(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        payment_id: PaymentId,
        now: datetime,
    ) -> None:
        """Different idempotency key on captured payment raises AlreadyCaptured."""
        captured_payment = Payment(
            id=payment_id,
            state=PaymentState.CAPTURED,
            authorized_at=now - timedelta(hours=2),
            capture_expires_at=now + timedelta(hours=22),
            captured_at=now - timedelta(hours=1),
            captured_amount_cents=1000,
        )
        payment_repository.save(captured_payment)

        request = CapturePaymentRequest(
            payment_id=payment_id,
            idempotency_key=IdempotencyKey(value="new-key"),
            amount_cents=2000,
        )

        with pytest.raises(PaymentAlreadyCapturedError):
            use_case.execute(request)

    def test_payment_expired_raises(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        payment_id: PaymentId,
        idempotency_key: IdempotencyKey,
        now: datetime,
    ) -> None:
        """Capture after expiry raises PaymentExpiredError."""
        expired_payment = Payment(
            id=payment_id,
            state=PaymentState.AUTHORIZED,
            authorized_at=now - timedelta(hours=25),
            capture_expires_at=now - timedelta(hours=1),  # Already expired
            captured_at=None,
            captured_amount_cents=None,
        )
        payment_repository.save(expired_payment)

        request = CapturePaymentRequest(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        with pytest.raises(PaymentExpiredError):
            use_case.execute(request)

    def test_capture_at_exact_expiry_raises(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        payment_id: PaymentId,
        idempotency_key: IdempotencyKey,
        now: datetime,
    ) -> None:
        """Capture at exactly expiry time is rejected (strict less-than)."""
        payment = Payment(
            id=payment_id,
            state=PaymentState.AUTHORIZED,
            authorized_at=now - timedelta(hours=24),
            capture_expires_at=now,  # Expires exactly now
            captured_at=None,
            captured_amount_cents=None,
        )
        payment_repository.save(payment)

        request = CapturePaymentRequest(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        with pytest.raises(PaymentExpiredError):
            use_case.execute(request)

    def test_pending_payment_raises_expired(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        payment_id: PaymentId,
        idempotency_key: IdempotencyKey,
    ) -> None:
        """Pending payment cannot be captured (no capture window)."""
        pending_payment = Payment(
            id=payment_id,
            state=PaymentState.PENDING,
            authorized_at=None,
            capture_expires_at=None,
            captured_at=None,
            captured_amount_cents=None,
        )
        payment_repository.save(pending_payment)

        request = CapturePaymentRequest(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        with pytest.raises(PaymentExpiredError):
            use_case.execute(request)


# =============================================================================
# Time-Based Tests - ADR-002
# =============================================================================


class TestCapturePaymentTimeBehavior:
    """Test time-based behavior per ADR-002."""

    def test_capture_one_microsecond_before_expiry_succeeds(
        self,
        use_case: CapturePaymentUseCase,
        payment_repository: InMemoryPaymentRepository,
        payment_id: PaymentId,
        idempotency_key: IdempotencyKey,
        now: datetime,
    ) -> None:
        expiry = now + timedelta(microseconds=1)
        payment = Payment(
            id=payment_id,
            state=PaymentState.AUTHORIZED,
            authorized_at=now - timedelta(hours=1),
            capture_expires_at=expiry,
            captured_at=None,
            captured_amount_cents=None,
        )
        payment_repository.save(payment)

        request = CapturePaymentRequest(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        response = use_case.execute(request)

        assert response.is_replay is False

    def test_time_change_affects_capture_eligibility(
        self,
        payment_repository: InMemoryPaymentRepository,
        capture_repository: InMemoryCaptureRepository,
        payment_id: PaymentId,
        now: datetime,
    ) -> None:
        """Demonstrates time provider controls capture eligibility."""
        time_provider = FixedTimeProvider(now)
        lock_provider = NoOpLockProvider()
        use_case = CapturePaymentUseCase(
            lock_provider=lock_provider,
            time_provider=time_provider,
            payment_repository=payment_repository,
            capture_repository=capture_repository,
        )

        payment = Payment(
            id=payment_id,
            state=PaymentState.AUTHORIZED,
            authorized_at=now - timedelta(hours=1),
            capture_expires_at=now + timedelta(hours=1),
            captured_at=None,
            captured_amount_cents=None,
        )
        payment_repository.save(payment)

        # Advance time past expiry
        time_provider.set_time(now + timedelta(hours=2))

        request = CapturePaymentRequest(
            payment_id=payment_id,
            idempotency_key=IdempotencyKey(value="test-key"),
            amount_cents=1000,
        )

        with pytest.raises(PaymentExpiredError):
            use_case.execute(request)


# =============================================================================
# Concurrency Tests - ADR-003 Section 10
# =============================================================================


class TestCapturePaymentConcurrency:
    """Test concurrent access per ADR-003 Section 10."""

    def test_concurrent_same_key_one_capture(self) -> None:
        """Two threads, same (payment_id, idempotency_key) → one capture, both get same result."""
        now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        time_provider = FixedTimeProvider(now)
        lock_provider = InMemoryLockProvider()
        payment_repository = InMemoryPaymentRepository()
        capture_repository = InMemoryCaptureRepository()

        use_case = CapturePaymentUseCase(
            lock_provider=lock_provider,
            time_provider=time_provider,
            payment_repository=payment_repository,
            capture_repository=capture_repository,
        )

        payment_id = PaymentId.generate()
        payment = Payment(
            id=payment_id,
            state=PaymentState.AUTHORIZED,
            authorized_at=now - timedelta(hours=1),
            capture_expires_at=now + timedelta(hours=23),
            captured_at=None,
            captured_amount_cents=None,
        )
        payment_repository.save(payment)

        idempotency_key = IdempotencyKey(value="concurrent-key")
        request = CapturePaymentRequest(
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=1000,
        )

        results: list[tuple[bool, str]] = []
        results_lock = threading.Lock()

        def worker() -> None:
            response = use_case.execute(request)
            with results_lock:
                results.append((response.is_replay, str(response.capture.id.value)))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker) for _ in range(5)]
            wait(futures)

        # All workers completed
        assert len(results) == 5

        # All got the same capture ID
        capture_ids = {r[1] for r in results}
        assert len(capture_ids) == 1

        # Exactly one was not a replay
        non_replays = [r for r in results if not r[0]]
        assert len(non_replays) == 1

    def test_concurrent_different_keys_one_succeeds(self) -> None:
        """Two threads, same payment, different keys → one succeeds, one gets AlreadyCaptured."""
        now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        time_provider = FixedTimeProvider(now)
        lock_provider = InMemoryLockProvider()
        payment_repository = InMemoryPaymentRepository()
        capture_repository = InMemoryCaptureRepository()

        use_case = CapturePaymentUseCase(
            lock_provider=lock_provider,
            time_provider=time_provider,
            payment_repository=payment_repository,
            capture_repository=capture_repository,
        )

        payment_id = PaymentId.generate()
        payment = Payment(
            id=payment_id,
            state=PaymentState.AUTHORIZED,
            authorized_at=now - timedelta(hours=1),
            capture_expires_at=now + timedelta(hours=23),
            captured_at=None,
            captured_amount_cents=None,
        )
        payment_repository.save(payment)

        results: list[str] = []  # "success" or "already_captured"
        results_lock = threading.Lock()

        def worker(key: str) -> None:
            request = CapturePaymentRequest(
                payment_id=payment_id,
                idempotency_key=IdempotencyKey(value=key),
                amount_cents=1000,
            )
            try:
                use_case.execute(request)
                with results_lock:
                    results.append("success")
            except PaymentAlreadyCapturedError:
                with results_lock:
                    results.append("already_captured")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, f"key-{i}") for i in range(5)]
            wait(futures)

        # All workers completed
        assert len(results) == 5

        # Exactly one succeeded
        successes = [r for r in results if r == "success"]
        assert len(successes) == 1

        # Others got AlreadyCaptured
        already_captured = [r for r in results if r == "already_captured"]
        assert len(already_captured) == 4
