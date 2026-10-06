import asyncio
import logging
from uuid import NAMESPACE_URL, uuid5

from ecosystem_shared import (
    PAYMENT_FAILED,
    PAYMENT_PROCESSED,
    BaseEvent,
    BrokerClient,
    OrderCreated,
    PaymentFailed,
    PaymentProcessed,
)

from payment_service.processor import PaymentProcessor
from payment_service.repository import PaymentRecord, PaymentRepository

logger = logging.getLogger("payment_service")

PUBLISH_TIMEOUT_SECONDS = 5


class OrderCreatedHandler:
    def __init__(
        self, broker: BrokerClient, processor: PaymentProcessor, repository: PaymentRepository
    ) -> None:
        self._broker = broker
        self._processor = processor
        self._repository = repository

    async def __call__(self, event: BaseEvent) -> None:
        if not isinstance(event, OrderCreated):
            raise TypeError(f"unexpected event type {event.event_type}")

        outcome = await self._processor.charge(event)

        # Deterministic ids: reprocessing the same order.created yields identical output,
        # so duplicates are harmless and downstream services can deduplicate them too.
        payment_id = uuid5(NAMESPACE_URL, f"payment:{event.order_id}")

        result: BaseEvent
        if outcome.approved:
            result = PaymentProcessed(
                event_id=uuid5(event.event_id, PAYMENT_PROCESSED),
                correlation_id=event.correlation_id,
                order_id=event.order_id,
                payment_id=payment_id,
                amount=event.total_amount,
                currency=event.currency,
            )
            status = "processed"
        else:
            result = PaymentFailed(
                event_id=uuid5(event.event_id, PAYMENT_FAILED),
                correlation_id=event.correlation_id,
                order_id=event.order_id,
                reason=outcome.reason or "unknown",
                amount=event.total_amount,
                currency=event.currency,
            )
            status = "failed"

        self._repository.save(
            PaymentRecord(
                payment_id=payment_id,
                order_id=event.order_id,
                amount=event.total_amount,
                currency=event.currency,
                status=status,
                reason=outcome.reason,
            )
        )

        async with asyncio.timeout(PUBLISH_TIMEOUT_SECONDS):
            await self._broker.publish(result)

        logger.info(
            "payment %s order_id=%s correlation_id=%s", status, event.order_id, event.correlation_id
        )
