from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from payments_core.domain.entities import Capture, PaymentState
from payments_core.domain.exceptions import (
    IdempotencyKeyReuseError,
    PaymentAlreadyCapturedError,
    PaymentExpiredError,
    PaymentNotFoundError,
)

if TYPE_CHECKING:
    from payments_core.application.ports import (
        CaptureRepository,
        LockProvider,
        PaymentRepository,
        TimeProvider,
    )
    from payments_core.domain.value_objects import IdempotencyKey, PaymentId


@dataclass(frozen=True, slots=True)
class CapturePaymentRequest:
    """Input DTO for capture payment use case."""

    payment_id: PaymentId
    idempotency_key: IdempotencyKey
    amount_cents: int


@dataclass(frozen=True, slots=True)
class CapturePaymentResponse:
    """Output DTO for capture payment use case."""

    capture: Capture
    is_replay: bool  # True if this was an idempotent replay


class CapturePaymentUseCase:
    """Orchestrates the capture payment workflow.

    Responsibilities:
    - Acquire per-payment lock (ADR-003)
    - Fetch current time inside lock (ADR-002)
    - Check idempotency FIRST (ADR-001 Section 7)
    - Validate business rules (ADR-001 Section 6)
    - Persist capture and update payment state

    This use case is the single entry point for capture operations.
    All concurrency, time, and persistence concerns are handled here.
    """

    def __init__(
        self,
        lock_provider: LockProvider,
        time_provider: TimeProvider,
        payment_repository: PaymentRepository,
        capture_repository: CaptureRepository,
    ) -> None:
        self._lock_provider = lock_provider
        self._time_provider = time_provider
        self._payment_repo = payment_repository
        self._capture_repo = capture_repository

    def execute(self, request: CapturePaymentRequest) -> CapturePaymentResponse:
        """Execute the capture payment workflow.

        Args:
            request: The capture request with payment_id, idempotency_key, amount.

        Returns:
            CapturePaymentResponse with the capture and replay indicator.

        Raises:
            PaymentNotFoundError: Payment does not exist.
            PaymentAlreadyCapturedError: Payment already captured (different key).
            PaymentExpiredError: Capture window has expired.
            IdempotencyKeyReuseError: Same key used with different amount.
        """
        # Step 1: Acquire lock (ADR-003)
        with self._lock_provider.acquire(str(request.payment_id.value)):
            return self._execute_within_lock(request)

    def _execute_within_lock(self, request: CapturePaymentRequest) -> CapturePaymentResponse:
        """Execute capture logic within the lock's critical section."""

        # Step 2: Fetch time INSIDE lock (ADR-002)
        now = self._time_provider.now()

        # Step 3: Check idempotency FIRST (ADR-001 Section 7)
        existing_capture = self._capture_repo.get_by_idempotency_key(
            request.payment_id, request.idempotency_key
        )
        if existing_capture is not None:
            return self._handle_idempotent_replay(existing_capture, request)

        # Step 4: Fetch payment
        payment = self._payment_repo.get(request.payment_id)
        if payment is None:
            raise PaymentNotFoundError(f"Payment not found: {request.payment_id.value}")

        # Step 5: Validate business rules (ADR-001 Section 6)
        if payment.state == PaymentState.CAPTURED:
            raise PaymentAlreadyCapturedError(
                f"Payment already captured: {request.payment_id.value}"
            )

        if not payment.can_capture(now):
            raise PaymentExpiredError(
                f"Capture window expired for payment: {request.payment_id.value}"
            )

        # Step 6: Create capture and update payment
        capture = Capture.create(
            payment_id=request.payment_id,
            idempotency_key=request.idempotency_key,
            amount_cents=request.amount_cents,
            created_at=now,
        )
        captured_payment = payment.capture(now, request.amount_cents)

        # Step 7: Persist (order: capture first, then payment)
        self._capture_repo.save(capture)
        self._payment_repo.save(captured_payment)

        return CapturePaymentResponse(capture=capture, is_replay=False)

    def _handle_idempotent_replay(
        self,
        existing_capture: Capture,
        request: CapturePaymentRequest,
    ) -> CapturePaymentResponse:
        """Handle replay of an existing capture.

        Per ADR-001 Section 7:
        - Exact match (same amount): return existing capture
        - Payload mismatch (different amount): raise IdempotencyKeyReuseError
        """
        if existing_capture.amount_cents != request.amount_cents:
            raise IdempotencyKeyReuseError(
                f"Idempotency key '{request.idempotency_key.value}' already used "
                f"with amount_cents={existing_capture.amount_cents}, "
                f"but request has amount_cents={request.amount_cents}"
            )

        return CapturePaymentResponse(capture=existing_capture, is_replay=True)
