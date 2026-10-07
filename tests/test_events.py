from decimal import Decimal
from uuid import uuid4

import pytest
from ecosystem_shared import (
    EVENT_REGISTRY,
    ORDER_CREATED,
    OrderCreated,
    OrderItem,
    PaymentFailed,
    PaymentProcessed,
)
from pydantic import ValidationError


def make_order() -> OrderCreated:
    return OrderCreated(
        correlation_id=uuid4(),
        order_id=uuid4(),
        customer_id="cust-1",
        items=[OrderItem(sku="ABC", quantity=2, unit_price=Decimal("10.50"))],
        total_amount=Decimal("21.00"),
    )


def test_order_created_json_roundtrip() -> None:
    event = make_order()
    restored = OrderCreated.model_validate_json(event.model_dump_json())
    assert restored == event
    assert restored.total_amount == Decimal("21.00")


def test_event_type_is_routing_key() -> None:
    assert OrderCreated.event_type == ORDER_CREATED


def test_registry_resolves_all_events() -> None:
    assert EVENT_REGISTRY["order.created"] is OrderCreated
    assert EVENT_REGISTRY["payment.processed"] is PaymentProcessed
    assert EVENT_REGISTRY["payment.failed"] is PaymentFailed


def test_invalid_quantity_rejected() -> None:
    with pytest.raises(ValidationError):
        OrderItem(sku="ABC", quantity=0, unit_price=Decimal("1"))


def test_empty_items_rejected() -> None:
    with pytest.raises(ValidationError):
        OrderCreated(
            correlation_id=uuid4(),
            order_id=uuid4(),
            customer_id="c",
            items=[],
            total_amount=Decimal("1"),
        )


def test_payment_failed_roundtrip_keeps_customer_id() -> None:
    event = PaymentFailed(
        correlation_id=uuid4(),
        order_id=uuid4(),
        customer_id="cust-9",
        reason="card declined",
        amount=Decimal("5.00"),
    )
    restored = PaymentFailed.model_validate_json(event.model_dump_json())
    assert restored == event
    assert restored.customer_id == "cust-9"
