from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from payments_core.application.ports.capture_repository import CaptureRepository
from payments_core.domain.exceptions import DuplicateCaptureError

if TYPE_CHECKING:
    from payments_core.domain.entities import Capture
    from payments_core.domain.value_objects import IdempotencyKey, PaymentId


class InMemoryCaptureRepository(CaptureRepository):
    """In-memory capture repository for testing and Stage 1.

    Implementation notes:
    - Keyed by (PaymentId, IdempotencyKey) tuple for O(1) lookup
    - Returns deep copies from get_by_idempotency_key()
    - NOT thread-safe; relies on external LockProvider for serialization
    """

    def __init__(self) -> None:
        self._captures: dict[tuple[PaymentId, IdempotencyKey], Capture] = {}

    def get_by_idempotency_key(
        self,
        payment_id: PaymentId,
        idempotency_key: IdempotencyKey,
    ) -> Capture | None:
        capture = self._captures.get((payment_id, idempotency_key))
        if capture is None:
            return None
        return copy.deepcopy(capture)

    def save(self, capture: Capture) -> None:
        key = (capture.payment_id, capture.idempotency_key)
        if key in self._captures:
            raise DuplicateCaptureError(
                f"Capture already exists for payment_id={capture.payment_id}, "
                f"idempotency_key={capture.idempotency_key}"
            )
        self._captures[key] = copy.deepcopy(capture)
