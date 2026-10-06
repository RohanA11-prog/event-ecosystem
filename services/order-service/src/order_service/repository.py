from uuid import UUID

from order_service.schemas import Order


class OrderRepository:
    """In-memory store. Data is lost on restart; a real service would use a database."""

    def __init__(self) -> None:
        self._orders: dict[UUID, Order] = {}

    def add(self, order: Order) -> None:
        self._orders[order.order_id] = order

    def get(self, order_id: UUID) -> Order | None:
        return self._orders.get(order_id)

    def remove(self, order_id: UUID) -> None:
        self._orders.pop(order_id, None)

    def __len__(self) -> int:
        return len(self._orders)
