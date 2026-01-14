from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class TimeProvider(ABC):
    """Port for time operations.

    Contract:
    - now() MUST return a datetime with tzinfo=datetime.UTC
    - now() MUST NOT return naive datetimes under any circumstance
    - Not just "timezone-aware"—specifically UTC (no -06:00 offsets)

    Naive datetime = bug. This is non-negotiable.
    """

    @abstractmethod
    def now(self) -> datetime:
        """Return the current UTC datetime (tzinfo=datetime.UTC)."""
        ...
