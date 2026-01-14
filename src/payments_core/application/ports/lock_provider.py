from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


class LockProvider(ABC):
    """Port for resource-level locking.

    Contract:
    - acquire() MUST serialize access to the same resource_id
    - acquire() MUST release the lock when the context exits (normal or exception)
    - acquire() MUST be blocking (waits until lock is available)
    - Different resource_ids MAY be acquired concurrently

    The context manager pattern ensures locks are always released,
    even when exceptions occur within the critical section.
    """

    @abstractmethod
    @contextmanager
    def acquire(self, resource_id: str) -> Iterator[None]:
        """Acquire a lock for the given resource ID.

        Args:
            resource_id: Canonical string identifier for the resource.
                         Must be stable and deterministic (e.g., str(payment_id.value)).

        Yields:
            None. The lock is held for the duration of the context.

        Usage:
            with lock_provider.acquire("payment-uuid-string"):
                # Critical section - lock is held
                ...
            # Lock is released here
        """
        ...
