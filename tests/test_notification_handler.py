from decimal import Decimal
from uuid import uuid4

import pytest
from ecosystem_shared import OrderCreated, OrderItem, PaymentFailed, PaymentProcessed
from notification_service.handlers import PaymentEventHandler
from notification_service.sender import NotificationError, NotificationSender
from notification_service.store import NotificationKind, NotificationStore


def make_handler() -> tuple[PaymentEventHandler, NotificationStore]:
    store = NotificationStore()
    return PaymentEventHandler(NotificationSender(latency=(0, 0)), store), store


def make_processed(customer_id: str = "cust-1") -> PaymentProcessed:
    return PaymentProcessed(
        correlation_id=uuid4(),
        order_id=uuid4(),
        customer_id=customer_id,
        payment_id=uuid4(),
        amount=Decimal("21.00"),
    )


async def test_payment_processed_creates_success_notification() -> None:
    handler, store = make_handler()
    event = make_processed()
    await handler(event)

    (notification,) = store.for_order(event.order_id)
    assert notification.kind == NotificationKind.PAYMENT_SUCCEEDED
    assert "21.00" in notification.body
    assert notification.correlation_id == event.correlation_id


async def test_payment_failed_notification_mentions_reason() -> None:
    handler, store = make_handler()
    event = PaymentFailed(
        correlation_id=uuid4(),
        order_id=uuid4(),
        customer_id="cust-1",
        reason="card declined",
        amount=Decimal("21.00"),
    )
    await handler(event)

    (notification,) = store.for_order(event.order_id)
    assert notification.kind == NotificationKind.PAYMENT_FAILED
    assert "card declined" in notification.body


async def test_sender_failure_raises_and_records_nothing() -> None:
    handler, store = make_handler()
    with pytest.raises(NotificationError):
        await handler(make_processed(customer_id="cust-notify-fail"))

    assert store.list_all() == []


async def test_unexpected_event_type_is_rejected() -> None:
    handler, _ = make_handler()
    order = OrderCreated(
        correlation_id=uuid4(),
        order_id=uuid4(),
        customer_id="cust-1",
        items=[OrderItem(sku="ABC", quantity=1, unit_price=Decimal("10"))],
        total_amount=Decimal("10"),
    )
    with pytest.raises(TypeError):
        await handler(order)
