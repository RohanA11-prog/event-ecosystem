import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, cast
from uuid import UUID

from ecosystem_shared import ORDER_CREATED, BrokerClient, EventConsumer
from fastapi import Depends, FastAPI, HTTPException, Request, status

from payment_service.config import QUEUE_ORDER_CREATED, PaymentSettings
from payment_service.handlers import OrderCreatedHandler
from payment_service.processor import PaymentProcessor
from payment_service.repository import PaymentRecord, PaymentRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("payment_service")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = PaymentSettings()
    broker = BrokerClient(settings.rabbitmq_url)
    await broker.connect()

    repository = PaymentRepository()
    handler = OrderCreatedHandler(broker, PaymentProcessor(), repository)
    consumer = EventConsumer(
        broker,
        queue_name=QUEUE_ORDER_CREATED,
        binding_keys=[ORDER_CREATED],
        handler=handler,
    )
    await consumer.start()

    app.state.repository = repository
    app.state.consumer = consumer
    logger.info("payment-service started")
    try:
        yield
    finally:
        await consumer.stop()
        await broker.close()
        logger.info("payment-service stopped")


app = FastAPI(title="Payment Service", lifespan=lifespan)


def get_repository(request: Request) -> PaymentRepository:
    return cast(PaymentRepository, request.app.state.repository)


RepoDep = Annotated[PaymentRepository, Depends(get_repository)]


@app.get("/payments/{order_id}", response_model=PaymentRecord)
async def get_payment(order_id: UUID, repo: RepoDep) -> PaymentRecord:
    record = repo.get_by_order(order_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return record
