"""Payment entity with state machine behavior.

See ADR-001 for domain model specification.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import TYPE_CHECKING

from payments_core.domain.exceptions import InvalidStateTransitionError

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from payments_core.domain.value_objects.payment_id import PaymentId


class PaymentState(Enum):
    """Payment lifecycle states per ADR-001 Section 2."""

    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Payment:
    """Payment entity with state machine behavior.

    This is a rich domain model where the entity encapsulates its own
    behavior and enforces state transitions internally. Invalid transitions
    raise InvalidStateTransitionError.

    Payment is immutable (frozen dataclass). All state-changing methods
    return a new Payment instance.

    State machine (ADR-001 Section 2):
        - pending → authorized (authorize)
        - authorized → captured (capture)
        - authorized → failed (fail)
        - captured is terminal (no further transitions)
    """

    id: PaymentId
    state: PaymentState
    authorized_at: datetime | None
    capture_expires_at: datetime | None
    captured_at: datetime | None
    captured_amount_cents: int | None

    def authorize(self, now: datetime, capture_window: timedelta) -> Payment:
        """Authorize the payment, setting the capture window.

        Args:
            now: Current timestamp (UTC).
            capture_window: Duration until capture expires.

        Returns:
            New Payment instance in AUTHORIZED state.

        Raises:
            InvalidStateTransitionError: If not in PENDING state.
        """
        if self.state != PaymentState.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot authorize payment in state {self.state.value}; "
                f"must be in {PaymentState.PENDING.value} state"
            )

        return replace(
            self,
            state=PaymentState.AUTHORIZED,
            authorized_at=now,
            capture_expires_at=now + capture_window,
        )

    def can_capture(self, now: datetime) -> bool:
        """Check if the payment can be captured at the given time.

        Per ADR-001 Section 6.3: capture only succeeds if now < capture_expires_at.

        Args:
            now: Current timestamp (UTC).

        Returns:
            True if capture is allowed, False otherwise.
        """
        if self.state != PaymentState.AUTHORIZED:
            return False

        if self.capture_expires_at is None:
            return False

        return now < self.capture_expires_at

    def capture(self, now: datetime, amount_cents: int) -> Payment:
        """Capture the payment.

        Args:
            now: Current timestamp (UTC).
            amount_cents: Amount to capture in cents.

        Returns:
            New Payment instance in CAPTURED state.

        Raises:
            InvalidStateTransitionError: If not in AUTHORIZED state.

        Note:
            This method does NOT check can_capture(). The use case is
            responsible for checking capture eligibility before calling
            this method. This separation allows the use case to raise
            appropriate domain exceptions (PaymentExpiredError, etc.).
        """
        if self.state != PaymentState.AUTHORIZED:
            raise InvalidStateTransitionError(
                f"Cannot capture payment in state {self.state.value}; "
                f"must be in {PaymentState.AUTHORIZED.value} state"
            )

        return replace(
            self,
            state=PaymentState.CAPTURED,
            captured_at=now,
            captured_amount_cents=amount_cents,
        )

    def fail(self) -> Payment:
        """Mark the payment as failed.

        Returns:
            New Payment instance in FAILED state.

        Raises:
            InvalidStateTransitionError: If not in AUTHORIZED state.
        """
        if self.state != PaymentState.AUTHORIZED:
            raise InvalidStateTransitionError(
                f"Cannot fail payment in state {self.state.value}; "
                f"must be in {PaymentState.AUTHORIZED.value} state"
            )

        return replace(self, state=PaymentState.FAILED)
