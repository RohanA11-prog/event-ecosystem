from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

import pytest
from ecosystem_shared import BaseEvent, OrderCreated, OrderItem, PaymentFailed, PaymentProcessed
from payment_service.handlers import OrderCreatedHandler
from payment_service.processor import PaymentProcessor, TransientPaymentError
from payment_service.repository import PaymentRepository


class FakeBroker:
    def __init__(self) -> None:
        self.published: list[BaseEvent] = []

    async def publish(self, event: BaseEvent) -> None:
        self.published.append(event)


def make_order(customer_id: str = "cust-1", total: str = "50.00") -> OrderCreated:
    return OrderCreated(
        correlation_id=uuid4(),
        order_id=uuid4(),
        customer_id=customer_id,
        items=[OrderItem(sku="ABC", quantity=1, unit_price=Decimal(total))],
        total_amount=Decimal(total),
    )


def make_handler(broker: FakeBroker) -> OrderCreatedHandler:
    return OrderCreatedHandler(
        cast(Any, broker), PaymentProcessor(latency=(0, 0)), PaymentRepository()
    )


async def test_approved_order_publishes_payment_processed() -> None:
    broker = FakeBroker()
    order = make_order()
    await make_handler(broker)(order)

    result = broker.published[0]
    assert isinstance(result, PaymentProcessed)
    assert result.order_id == order.order_id
    assert result.correlation_id == order.correlation_id


async def test_declined_customer_publishes_payment_failed() -> None:
    broker = FakeBroker()
    await make_handler(broker)(make_order(customer_id="cust-declined"))

    result = broker.published[0]
    assert isinstance(result, PaymentFailed)
    assert result.reason == "card declined"


async def test_amount_over_limit_is_declined() -> None:
    broker = FakeBroker()
    await make_handler(broker)(make_order(total="1500.00"))

    result = broker.published[0]
    assert isinstance(result, PaymentFailed)
    assert result.reason == "amount exceeds limit"


async def test_reprocessing_same_event_yields_identical_output() -> None:
    broker = FakeBroker()
    handler = make_handler(broker)
    order = make_order()
    await handler(order)
    await handler(order)

    first, second = broker.published
    assert isinstance(first, PaymentProcessed) and isinstance(second, PaymentProcessed)
    assert first.event_id == second.event_id
    assert first.payment_id == second.payment_id


async def test_flaky_customer_fails_twice_then_succeeds() -> None:
    broker = FakeBroker()
    handler = make_handler(broker)
    order = make_order(customer_id="cust-flaky")

    for _ in range(2):
        with pytest.raises(TransientPaymentError):
            await handler(order)
    await handler(order)

    assert isinstance(broker.published[0], PaymentProcessed)
