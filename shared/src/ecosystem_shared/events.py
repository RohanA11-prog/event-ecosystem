"""Event contracts. These models ARE the public API between services."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ecosystem_shared.constants import ORDER_CREATED, PAYMENT_FAILED, PAYMENT_PROCESSED


class BaseEvent(BaseModel):
    """Metadata every event carries."""

    model_config = ConfigDict(frozen=True)

    event_type: ClassVar[str]  # the routing key; defined by each subclass

    event_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID  # same value across the whole order -> payment -> notification flow
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: int = 1


class OrderItem(BaseModel):
    sku: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0)


class OrderCreated(BaseEvent):
    event_type: ClassVar[str] = ORDER_CREATED

    order_id: UUID
    customer_id: str
    items: list[OrderItem] = Field(min_length=1)
    total_amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class PaymentProcessed(BaseEvent):
    event_type: ClassVar[str] = PAYMENT_PROCESSED

    order_id: UUID
    payment_id: UUID
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class PaymentFailed(BaseEvent):
    event_type: ClassVar[str] = PAYMENT_FAILED

    order_id: UUID
    reason: str
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


# Lets a consumer map an incoming routing key to the right model.
EVENT_REGISTRY: dict[str, type[BaseEvent]] = {
    cls.event_type: cls for cls in (OrderCreated, PaymentProcessed, PaymentFailed)
}
