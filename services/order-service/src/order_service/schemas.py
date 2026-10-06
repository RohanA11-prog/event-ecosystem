from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from ecosystem_shared import OrderItem
from pydantic import BaseModel, Field


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"


class CreateOrderRequest(BaseModel):
    customer_id: str = Field(min_length=1)
    items: list[OrderItem] = Field(min_length=1)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class Order(BaseModel):
    order_id: UUID
    correlation_id: UUID
    customer_id: str
    items: list[OrderItem]
    total_amount: Decimal
    currency: str
    status: OrderStatus
