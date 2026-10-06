from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PaymentRecord(BaseModel):
    payment_id: UUID
    order_id: UUID
    amount: Decimal
    currency: str
    status: str  # "processed" or "failed"
    reason: str | None = None


class PaymentRepository:
    """In-memory store keyed by order id. Saving twice for the same order just overwrites."""

    def __init__(self) -> None:
        self._by_order: dict[UUID, PaymentRecord] = {}

    def save(self, record: PaymentRecord) -> None:
        self._by_order[record.order_id] = record

    def get_by_order(self, order_id: UUID) -> PaymentRecord | None:
        return self._by_order.get(order_id)
