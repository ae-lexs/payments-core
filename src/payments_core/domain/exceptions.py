"""Domain exceptions for payments-core.

Exception hierarchy:
    DomainException (base)
    ├── State & Transition Errors
    │   ├── InvalidStateTransitionError
    │   ├── PaymentExpiredError
    │   └── PaymentAlreadyCapturedError
    ├── Not Found Errors
    │   └── PaymentNotFoundError
    ├── Validation Errors
    │   ├── InvalidPaymentIdError
    │   ├── InvalidIdempotencyKeyError
    │   └── InvalidAmountError
    └── Idempotency & Invariant Errors
        ├── IdempotencyKeyReuseError (client misuse, HTTP 409)
        └── DuplicateCaptureError (invariant violation)

See ADR-001 Section 8 and ADR-004 for exception semantics.
"""

from __future__ import annotations


class DomainException(Exception):
    """Base exception for all domain-level errors.

    All domain exceptions inherit from this class to enable
    catching domain errors distinctly from infrastructure errors.
    """


# =============================================================================
# State & Transition Errors
# =============================================================================


class InvalidStateTransitionError(DomainException):
    """Raised when a state transition violates the payment state machine.

    Valid transitions (ADR-001 Section 2):
        - pending → authorized
        - authorized → captured
        - authorized → failed

    Examples of invalid transitions:
        - pending → captured (must authorize first)
        - captured → anything (terminal state)
        - failed → anything
    """


class PaymentExpiredError(DomainException):
    """Raised when capture is attempted after the capture window expires.

    Per ADR-001 Section 6.3: capture only succeeds if now < capture_expires_at.
    The payment remains in AUTHORIZED state (no auto-transition on expiry).
    """


class PaymentAlreadyCapturedError(DomainException):
    """Raised when capture is attempted on an already captured payment.

    Per ADR-001 Section 6.4: if payment.state == CAPTURED, all future
    capture attempts are rejected—even with new idempotency keys.
    """


# =============================================================================
# Not Found Errors
# =============================================================================


class PaymentNotFoundError(DomainException):
    """Raised when a payment cannot be found by ID.

    This is a client error (HTTP 404) indicating the requested
    payment does not exist.
    """


# =============================================================================
# Validation Errors
# =============================================================================


class InvalidPaymentIdError(DomainException):
    """Raised when a payment ID fails validation.

    Per ADR-001 Section 5: PaymentId must be a valid UUID v4.
    """


class InvalidIdempotencyKeyError(DomainException):
    """Raised when an idempotency key fails validation.

    Per ADR-001 Section 5: IdempotencyKey must be non-empty, max 64 chars.
    """


class InvalidAmountError(DomainException):
    """Raised when amount_cents fails validation.

    Per ADR-001 Section 6.6: amount_cents must be greater than 0.
    Enforced in Capture.create() factory method (ADR-004 Section 4).
    """


# =============================================================================
# Idempotency & Invariant Errors
# =============================================================================


class IdempotencyKeyReuseError(DomainException):
    """Raised when an idempotency key is reused with different payload.

    This is a CLIENT ERROR (HTTP 409 Conflict).

    Per ADR-001 Section 7: if a capture with (payment_id, idempotency_key)
    exists but amount_cents differs from the request, this error is raised.
    The existing capture is not mutated.

    This indicates client misuse—the client should use a new idempotency
    key for requests with different parameters.
    """


class DuplicateCaptureError(DomainException):
    """Raised when repository save encounters a duplicate capture.

    This is an INVARIANT VIOLATION, not a client error.

    Per ADR-004 Section 3: should never happen if the use case checks
    idempotency first inside the lock. If raised, it indicates a
    programming error in the use case logic.

    Distinct from IdempotencyKeyReuseError:
        - IdempotencyKeyReuseError = client sent same key with different amount
        - DuplicateCaptureError = bug in use case (skipped idempotency check)
    """
