import asyncio
import random
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from ecosystem_shared import OrderCreated

AMOUNT_LIMIT = Decimal("1000")


class TransientPaymentError(Exception):
    """The gateway had a temporary problem; retrying may succeed."""


@dataclass(frozen=True)
class PaymentOutcome:
    approved: bool
    reason: str | None = None


class PaymentProcessor:
    def __init__(self, latency: tuple[float, float] = (0.2, 0.6)) -> None:
        self._latency = latency
        self._flaky_attempts: dict[UUID, int] = {}

    async def charge(self, order: OrderCreated) -> PaymentOutcome:
        # Simulated gateway latency. asyncio.sleep yields to the event loop;
        # time.sleep would freeze it.
        await asyncio.sleep(random.uniform(*self._latency))

        if order.customer_id == "cust-flaky":
            attempts = self._flaky_attempts.get(order.order_id, 0) + 1
            self._flaky_attempts[order.order_id] = attempts
            if attempts <= 2:
                raise TransientPaymentError(f"gateway timeout (attempt {attempts})")

        if order.customer_id == "cust-declined":
            return PaymentOutcome(approved=False, reason="card declined")
        if order.total_amount > AMOUNT_LIMIT:
            return PaymentOutcome(approved=False, reason="amount exceeds limit")
        return PaymentOutcome(approved=True)
