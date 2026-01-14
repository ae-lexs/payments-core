from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from payments_core.domain.value_objects import CaptureId, IdempotencyKey, PaymentId


@dataclass(frozen=True, slots=True)
class Capture:
    id: CaptureId
    payment_id: PaymentId
    idempotency_key: IdempotencyKey
    amount_cents: int
    created_at: datetime
