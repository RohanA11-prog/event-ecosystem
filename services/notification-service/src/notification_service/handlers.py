from uuid import UUID

from ecosystem_shared import BaseEvent, PaymentFailed, PaymentProcessed

from notification_service.sender import NotificationSender
from notification_service.store import Notification, NotificationKind, NotificationStore


class PaymentEventHandler:
    def __init__(self, sender: NotificationSender, store: NotificationStore) -> None:
        self._sender = sender
        self._store = store

    async def __call__(self, event: BaseEvent) -> None:
        if isinstance(event, PaymentProcessed):
            await self._notify(
                kind=NotificationKind.PAYMENT_SUCCEEDED,
                order_id=event.order_id,
                customer_id=event.customer_id,
                correlation_id=event.correlation_id,
                subject="Payment received",
                body=(
                    f"We received your payment of {event.amount} {event.currency} "
                    f"for order {event.order_id}."
                ),
            )
        elif isinstance(event, PaymentFailed):
            await self._notify(
                kind=NotificationKind.PAYMENT_FAILED,
                order_id=event.order_id,
                customer_id=event.customer_id,
                correlation_id=event.correlation_id,
                subject="Payment failed",
                body=(
                    f"Your payment of {event.amount} {event.currency} for order "
                    f"{event.order_id} failed: {event.reason}."
                ),
            )
        else:
            raise TypeError(f"unexpected event type {event.event_type}")

    async def _notify(
        self,
        *,
        kind: NotificationKind,
        order_id: UUID,
        customer_id: str,
        correlation_id: UUID,
        subject: str,
        body: str,
    ) -> None:
        # Send first; only record the notification once sending succeeded.
        await self._sender.send(customer_id, subject, body)
        self._store.add(
            Notification(
                order_id=order_id,
                customer_id=customer_id,
                correlation_id=correlation_id,
                kind=kind,
                subject=subject,
                body=body,
            )
        )
