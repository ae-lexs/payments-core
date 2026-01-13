"""Domain exceptions - Business rule violations."""


class DomainException(Exception):
    """Base exception for all domain-level errors."""


class InvalidStateTransitionError(DomainException):
    """Raised when an invalid payment state transition is attempted."""


class PaymentExpiredError(DomainException):
    """Raised when attempting to capture an expired authorization."""


class PaymentAlreadyCapturedError(DomainException):
    """Raised when attempting to capture an already captured payment."""
