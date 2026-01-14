from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from payments_core.domain.exceptions import InvalidCaptureIdError


@dataclass(frozen=True, slots=True)
class CaptureId:
    """Value object for capture identifiers.

    Per ADR-001 Section 5: CaptureId must be a valid UUID v4.
    """

    value: UUID

    @classmethod
    def generate(cls) -> CaptureId:
        """Generate a new unique CaptureId."""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, id_str: str) -> CaptureId:
        """Parse a CaptureId from a string representation.

        Args:
            id_str: UUID string (with or without hyphens, any case).

        Returns:
            A CaptureId instance.

        Raises:
            InvalidCaptureIdError: If the string is not a valid UUID.
        """
        try:
            return cls(value=UUID(id_str))
        except (ValueError, AttributeError) as e:
            raise InvalidCaptureIdError(f"Invalid capture ID: {id_str}") from e
