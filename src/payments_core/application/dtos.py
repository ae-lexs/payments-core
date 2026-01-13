"""Data Transfer Objects for use case input/output."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CapturePaymentRequest:
    """Input DTO for the CapturePayment use case."""

    payment_id: str
    idempotency_key: str
    amount_cents: int


@dataclass(frozen=True)
class CapturePaymentResponse:
    """Output DTO for the CapturePayment use case."""

    capture_id: str
    payment_id: str
    status: str
    amount_cents: int
