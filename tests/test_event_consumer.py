from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

from ecosystem_shared import BaseEvent, BrokerClient, EventConsumer, OrderCreated, OrderItem


def make_event() -> OrderCreated:
    return OrderCreated(
        correlation_id=uuid4(),
        order_id=uuid4(),
        customer_id="cust-1",
        items=[OrderItem(sku="ABC", quantity=1, unit_price=Decimal("10"))],
        total_amount=Decimal("10"),
    )


class FakeMessage:
    def __init__(self, event: BaseEvent | None = None, body: bytes | None = None) -> None:
        self.body = (
            body if body is not None else (event.model_dump_json().encode() if event else b"")
        )
        self.routing_key = event.event_type if event else None
        self.type = event.event_type if event else None
        self.acked = False
        self.rejected = False
        self.requeue: bool | None = None

    async def ack(self) -> None:
        self.acked = True

    async def reject(self, requeue: bool = False) -> None:
        self.rejected = True
        self.requeue = requeue


def make_consumer(handler: object) -> EventConsumer:
    return EventConsumer(
        BrokerClient("amqp://unused"),
        queue_name="test.queue",
        binding_keys=["order.created"],
        handler=cast(Any, handler),
        max_attempts=3,
        base_delay=0,
    )


async def deliver(consumer: EventConsumer, message: FakeMessage) -> None:
    await consumer.handle_message(cast(Any, message))


async def test_success_acks_message() -> None:
    calls: list[BaseEvent] = []

    async def handler(event: BaseEvent) -> None:
        calls.append(event)

    event = make_event()
    message = FakeMessage(event)
    await deliver(make_consumer(handler), message)

    assert calls == [event]
    assert message.acked


async def test_duplicate_event_is_skipped_but_acked() -> None:
    calls: list[BaseEvent] = []

    async def handler(event: BaseEvent) -> None:
        calls.append(event)

    consumer = make_consumer(handler)
    event = make_event()
    first, second = FakeMessage(event), FakeMessage(event)
    await deliver(consumer, first)
    await deliver(consumer, second)

    assert len(calls) == 1
    assert first.acked and second.acked


async def test_transient_failure_is_retried_then_succeeds() -> None:
    attempts = 0

    async def handler(event: BaseEvent) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("temporary")

    message = FakeMessage(make_event())
    await deliver(make_consumer(handler), message)

    assert attempts == 3
    assert message.acked


async def test_exhausted_retries_reject_without_requeue() -> None:
    attempts = 0

    async def handler(event: BaseEvent) -> None:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("permanent")

    message = FakeMessage(make_event())
    await deliver(make_consumer(handler), message)

    assert attempts == 3
    assert message.rejected and message.requeue is False
    assert not message.acked


async def test_undecodable_message_is_rejected() -> None:
    async def handler(event: BaseEvent) -> None:
        raise AssertionError("handler must not be called")

    message = FakeMessage(body=b"not json")
    await deliver(make_consumer(handler), message)

    assert message.rejected and message.requeue is False
