from collections.abc import Iterator
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest
from ecosystem_shared import BaseEvent, OrderCreated
from order_service.main import app, get_broker, get_repository
from order_service.repository import OrderRepository


class FakeBroker:
    def __init__(self) -> None:
        self.published: list[BaseEvent] = []
        self.fail = False

    async def publish(self, event: BaseEvent) -> None:
        if self.fail:
            raise ConnectionError("broker down")
        self.published.append(event)


@pytest.fixture
def repo() -> OrderRepository:
    return OrderRepository()


@pytest.fixture
def broker() -> FakeBroker:
    return FakeBroker()


@pytest.fixture(autouse=True)
def _overrides(repo: OrderRepository, broker: FakeBroker) -> Iterator[None]:
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_broker] = lambda: broker
    yield
    app.dependency_overrides.clear()


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


VALID_BODY = {
    "customer_id": "cust-1",
    "items": [{"sku": "ABC", "quantity": 2, "unit_price": "10.50"}],
}


async def test_create_order_publishes_event(broker: FakeBroker) -> None:
    async with make_client() as client:
        response = await client.post("/orders", json=VALID_BODY)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending_payment"
    assert Decimal(body["total_amount"]) == Decimal("21.00")
    assert len(broker.published) == 1
    event = broker.published[0]
    assert isinstance(event, OrderCreated)
    assert event.event_type == "order.created"
    assert event.order_id == UUID(body["order_id"])


async def test_invalid_order_is_rejected(broker: FakeBroker) -> None:
    async with make_client() as client:
        response = await client.post("/orders", json={"customer_id": "c", "items": []})

    assert response.status_code == 422
    assert broker.published == []


async def test_publish_failure_returns_503_and_rolls_back(
    broker: FakeBroker, repo: OrderRepository
) -> None:
    broker.fail = True
    async with make_client() as client:
        response = await client.post("/orders", json=VALID_BODY)

    assert response.status_code == 503
    assert len(repo) == 0


async def test_unknown_order_returns_404() -> None:
    async with make_client() as client:
        response = await client.get(f"/orders/{uuid4()}")

    assert response.status_code == 404
