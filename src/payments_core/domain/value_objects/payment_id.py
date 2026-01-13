from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class PaymentId:
    value: UUID

    @classmethod
    def generate(cls) -> PaymentId:
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, id_str: str) -> PaymentId:
        return cls(value=UUID(id_str))
