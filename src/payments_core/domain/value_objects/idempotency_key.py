from __future__ import annotations

from dataclasses import dataclass

from payments_core.domain.exceptions import InvalidIdempotencyKeyError

MAX_LENGTH = 64
ALLOWED_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:./")


@dataclass(frozen=True)
class IdempotencyKey:
    """Domain value object for idempotency keys.

    Per ADR-001 Section 5:
      - Non-empty, max 64 chars
      - Whitespace is trimmed (normalization)
      - ASCII charset only: [A-Za-z0-9-_:./]
    """

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()

        if normalized != self.value:
            object.__setattr__(self, "value", normalized)

        if not normalized:
            raise InvalidIdempotencyKeyError("Idempotency key cannot be empty")

        if len(normalized) > MAX_LENGTH:
            raise InvalidIdempotencyKeyError(
                f"Idempotency key cannot exceed {MAX_LENGTH} characters"
            )

        if any(ch not in ALLOWED_CHARS for ch in normalized):
            raise InvalidIdempotencyKeyError(
                "Idempotency key contains invalid characters; allowed: [A-Za-z0-9-_:./]"
            )
