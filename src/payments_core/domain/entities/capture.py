from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from payments_core.domain.exceptions import InvalidAmountError
from payments_core.domain.value_objects import CaptureId, IdempotencyKey, PaymentId

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class Capture:
    """Capture entity representing a successful payment capture.

    Per ADR-001 Section 3: Only successful captures are stored.
    Existence of a Capture record implies success.

    Use the create() factory method to construct instances with validation.
    """

    id: CaptureId
    payment_id: PaymentId
    idempotency_key: IdempotencyKey
    amount_cents: int
    created_at: datetime

    @classmethod
    def create(
        cls,
        payment_id: PaymentId,
        idempotency_key: IdempotencyKey,
        amount_cents: int,
        created_at: datetime,
    ) -> Capture:
        """Factory method to create a Capture with validation.

        Args:
            payment_id: The payment this capture belongs to.
            idempotency_key: Client-provided idempotency key.
            amount_cents: Amount captured in cents.
            created_at: Timestamp of capture creation (UTC).

        Returns:
            A new Capture instance.

        Raises:
            InvalidAmountError: If amount_cents <= 0.
        """
        if amount_cents <= 0:
            raise InvalidAmountError(f"Capture amount must be greater than 0, got {amount_cents}")

        return cls(
            id=CaptureId.generate(),
            payment_id=payment_id,
            idempotency_key=idempotency_key,
            amount_cents=amount_cents,
            created_at=created_at,
        )
