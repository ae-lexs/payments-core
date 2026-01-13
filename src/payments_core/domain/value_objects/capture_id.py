from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CaptureId:
    value: UUID

    @classmethod
    def generate(cls) -> CaptureId:
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, id_str: str) -> CaptureId:
        return cls(value=UUID(id_str))
