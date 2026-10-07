import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, cast
from uuid import UUID

from ecosystem_shared import PAYMENT_FAILED, PAYMENT_PROCESSED, BrokerClient, EventConsumer
from fastapi import Depends, FastAPI, Request

from notification_service.config import QUEUE_PAYMENT_EVENTS, NotificationSettings
from notification_service.handlers import PaymentEventHandler
from notification_service.sender import NotificationSender
from notification_service.store import Notification, NotificationStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("notification_service")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = NotificationSettings()
    broker = BrokerClient(settings.rabbitmq_url)
    await broker.connect()

    store = NotificationStore()
    handler = PaymentEventHandler(NotificationSender(), store)
    consumer = EventConsumer(
        broker,
        queue_name=QUEUE_PAYMENT_EVENTS,
        binding_keys=[PAYMENT_PROCESSED, PAYMENT_FAILED],
        handler=handler,
    )
    await consumer.start()

    app.state.store = store
    app.state.consumer = consumer
    logger.info("notification-service started")
    try:
        yield
    finally:
        await consumer.stop()
        await broker.close()
        logger.info("notification-service stopped")


app = FastAPI(title="Notification Service", lifespan=lifespan)


def get_store(request: Request) -> NotificationStore:
    return cast(NotificationStore, request.app.state.store)


StoreDep = Annotated[NotificationStore, Depends(get_store)]


@app.get("/notifications", response_model=list[Notification])
async def list_notifications(store: StoreDep) -> list[Notification]:
    return store.list_all()


@app.get("/notifications/{order_id}", response_model=list[Notification])
async def notifications_for_order(order_id: UUID, store: StoreDep) -> list[Notification]:
    return store.for_order(order_id)
