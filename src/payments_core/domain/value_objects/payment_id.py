from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from payments_core.domain.exceptions import InvalidPaymentIdError


@dataclass(frozen=True, slots=True)
class PaymentId:
    """Value object for payment identifiers.

    Per ADR-001 Section 5: PaymentId must be a valid UUID v4.
    """

    value: UUID

    @classmethod
    def generate(cls) -> PaymentId:
        """Generate a new unique PaymentId."""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, id_str: str) -> PaymentId:
        """Parse a PaymentId from a string representation.

        Args:
            id_str: UUID string (with or without hyphens, any case).

        Returns:
            A PaymentId instance.

        Raises:
            InvalidPaymentIdError: If the string is not a valid UUID.
        """
        try:
            return cls(value=UUID(id_str))
        except (ValueError, AttributeError) as e:
            raise InvalidPaymentIdError(f"Invalid payment ID: {id_str}") from e
