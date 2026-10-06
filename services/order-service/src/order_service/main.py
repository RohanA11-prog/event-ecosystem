import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Annotated, cast
from uuid import UUID, uuid4

from ecosystem_shared import BrokerClient, OrderCreated
from fastapi import Depends, FastAPI, HTTPException, Request, status

from order_service.config import OrderSettings
from order_service.repository import OrderRepository
from order_service.schemas import CreateOrderRequest, Order, OrderStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("order_service")

PUBLISH_TIMEOUT_SECONDS = 5


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = OrderSettings()
    broker = BrokerClient(settings.rabbitmq_url)
    await broker.connect()
    app.state.broker = broker
    app.state.repository = OrderRepository()
    logger.info("order-service started; connected to broker")
    try:
        yield
    finally:
        await broker.close()
        logger.info("order-service stopped")


app = FastAPI(title="Order Service", lifespan=lifespan)


def get_broker(request: Request) -> BrokerClient:
    return cast(BrokerClient, request.app.state.broker)


def get_repository(request: Request) -> OrderRepository:
    return cast(OrderRepository, request.app.state.repository)


BrokerDep = Annotated[BrokerClient, Depends(get_broker)]
RepoDep = Annotated[OrderRepository, Depends(get_repository)]


@app.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(body: CreateOrderRequest, broker: BrokerDep, repo: RepoDep) -> Order:
    total = sum((i.unit_price * i.quantity for i in body.items), start=Decimal(0))
    order = Order(
        order_id=uuid4(),
        correlation_id=uuid4(),
        customer_id=body.customer_id,
        items=body.items,
        total_amount=total,
        currency=body.currency.upper(),
        status=OrderStatus.PENDING_PAYMENT,
    )
    repo.add(order)

    event = OrderCreated(
        correlation_id=order.correlation_id,
        order_id=order.order_id,
        customer_id=order.customer_id,
        items=order.items,
        total_amount=order.total_amount,
        currency=order.currency,
    )
    try:
        async with asyncio.timeout(PUBLISH_TIMEOUT_SECONDS):
            await broker.publish(event)
    except Exception as exc:
        # Dual-write failure: the order was saved but the event could not be published.
        # Roll back so we never keep an order that nobody will ever process.
        repo.remove(order.order_id)
        logger.exception("failed to publish order.created for order %s", order.order_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not publish order event; please retry",
        ) from exc

    logger.info("order created order_id=%s correlation_id=%s", order.order_id, order.correlation_id)
    return order


@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: UUID, repo: RepoDep) -> Order:
    order = repo.get(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order
