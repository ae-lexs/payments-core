"""Locking mechanisms for concurrency control."""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from threading import Lock
from typing import Iterator


class LockProvider(ABC):
    """Abstract lock provider for payment-level serialization."""

    @abstractmethod
    @contextmanager
    def acquire(self, resource_id: str) -> Iterator[None]:
        """Acquire a lock for the given resource ID."""


class InMemoryLockProvider(LockProvider):
    """In-memory lock provider for single-process testing."""

    def __init__(self) -> None:
        self._locks: dict[str, Lock] = {}
        self._global_lock = Lock()

    @contextmanager
    def acquire(self, resource_id: str) -> Iterator[None]:
        with self._global_lock:
            if resource_id not in self._locks:
                self._locks[resource_id] = Lock()
            lock = self._locks[resource_id]

        lock.acquire()
        try:
            yield
        finally:
            lock.release()
