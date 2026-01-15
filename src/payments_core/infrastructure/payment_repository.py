from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from payments_core.application.ports import PaymentRepository

if TYPE_CHECKING:
    from payments_core.domain.entities import Payment
    from payments_core.domain.value_objects import PaymentId


class InMemoryPaymentRepository(PaymentRepository):
    """In-memory payment repository for testing and Stage 1.

    Implementation notes:
    - Uses dict with PaymentId as key (requires frozen dataclass)
    - Returns deep copies from get() to mimic database detachment
    - Stores deep copies in save() to prevent external mutation
    - NOT thread-safe; relies on external LockProvider for serialization

    Copy-on-read rationale:
    Returning copies catches bugs where code mutates an entity without
    calling save(). This mimics ORM behavior where fetched entities are
    detached from the session until explicitly merged/committed.

    Deepcopy assumptions:
    - All entities and value objects must be deepcopy-safe (frozen dataclasses are)
    - datetime objects with tzinfo=UTC survive deepcopy correctly
    - No external references (file handles, connections) in entities
    """

    def __init__(self) -> None:
        self._payments: dict[PaymentId, Payment] = {}

    def get(self, payment_id: PaymentId) -> Payment | None:
        payment = self._payments.get(payment_id)
        if payment is None:
            return None
        return copy.deepcopy(payment)

    def save(self, payment: Payment) -> None:
        self._payments[payment.id] = copy.deepcopy(payment)
