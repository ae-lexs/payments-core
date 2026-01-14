from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from payments_core.domain.entities.capture import Capture
    from payments_core.domain.value_objects import IdempotencyKey, PaymentId


class CaptureRepository(ABC):
    """Port for capture persistence.

    Contract:
    - Only successful captures are stored (existence implies success)
    - get_by_idempotency_key() is scoped to a specific payment
    - Implementations are NOT thread-safe; callers must ensure serialization

    Design note:
    We do not store rejected capture attempts. Audit trail for rejections
    is deferred to a future ADR. This simplifies the model: if a Capture
    record exists for (payment_id, idempotency_key), it succeeded.
    """

    @abstractmethod
    def get_by_idempotency_key(
        self,
        payment_id: PaymentId,
        idempotency_key: IdempotencyKey,
    ) -> Capture | None:
        """Retrieve a capture by payment ID and idempotency key.

        Args:
            payment_id: The payment identifier.
            idempotency_key: The client-provided idempotency key.

        Returns:
            The Capture entity if found, None otherwise.
            Returned entity is a copy; mutations do not affect stored state.
        """

    @abstractmethod
    def save(self, capture: Capture) -> None:
        """Persist a successful capture.

        Args:
            capture: The capture entity to save.

        Raises:
            DuplicateCaptureError: If (payment_id, idempotency_key) already exists.
                This is an invariant violation—should never happen if the use case
                checks idempotency first inside the lock. Distinct from
                IdempotencyKeyReuseError, which is client misuse (HTTP 409).
        """

    ...
