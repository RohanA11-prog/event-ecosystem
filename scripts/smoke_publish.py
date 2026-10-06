import asyncio
from decimal import Decimal
from uuid import uuid4

from ecosystem_shared import BrokerClient, BrokerSettings, OrderCreated, OrderItem


async def main() -> None:
    settings = BrokerSettings()
    broker = BrokerClient(settings.rabbitmq_url)
    await broker.connect()
    try:
        event = OrderCreated(
            correlation_id=uuid4(),
            order_id=uuid4(),
            customer_id="cust-1",
            items=[OrderItem(sku="ABC", quantity=1, unit_price=Decimal("19.99"))],
            total_amount=Decimal("19.99"),
        )
        await broker.publish(event)
        print(f"Published {event.event_type}: {event.event_id}")
    finally:
        await broker.close()


if __name__ == "__main__":
    asyncio.run(main())
