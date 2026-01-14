from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from payments_core.domain.entities import Payment
    from payments_core.domain.value_objects import PaymentId


class PaymentRepository(ABC):
    """Port for payment persistence.

    Contract:
    - get() returns None if payment does not exist (no exception)
    - save() performs upsert: creates if new, updates if exists
    - Implementations are NOT thread-safe; callers must ensure serialization
    - PaymentId is immutable after entity creation

    Thread safety note:
    Repositories assume the caller has acquired appropriate locks via
    LockProvider before invoking methods. This matches database behavior
    where transaction isolation is external to the repository.
    """

    @abstractmethod
    def get(self, payment_id: PaymentId) -> Payment | None:
        """Retrieve a payment by ID.

        Args:
            payment_id: The payment identifier.

        Returns:
            The Payment entity if found, None otherwise.
            Returned entity is a copy; mutations do not affect stored state.
        """

    @abstractmethod
    def save(self, payment: Payment) -> None:
        """Persist a payment (upsert semantics).

        Args:
            payment: The payment entity to save.

        Creates the payment if it doesn't exist, updates if it does.
        The payment.id must not change between creation and updates.
        """
