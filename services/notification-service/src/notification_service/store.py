from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class NotificationKind(StrEnum):
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"


class Notification(BaseModel):
    notification_id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    customer_id: str
    correlation_id: UUID
    kind: NotificationKind
    channel: str = "email"
    subject: str
    body: str
    sent_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationStore:
    """In-memory record of notifications that were successfully sent."""

    def __init__(self) -> None:
        self._items: list[Notification] = []

    def add(self, notification: Notification) -> None:
        self._items.append(notification)

    def list_all(self) -> list[Notification]:
        return list(self._items)

    def for_order(self, order_id: UUID) -> list[Notification]:
        return [n for n in self._items if n.order_id == order_id]
