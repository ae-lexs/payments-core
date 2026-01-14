"""Ports - Abstract interfaces for external dependencies.

Ports define the contracts that infrastructure adapters must implement.
This allows the application layer to remain decoupled from concrete implementations.
"""

from payments_core.application.ports.capture_repository import CaptureRepository
from payments_core.application.ports.payment_repository import PaymentRepository

__all__ = [
    "CaptureRepository",
    "PaymentRepository",
]
