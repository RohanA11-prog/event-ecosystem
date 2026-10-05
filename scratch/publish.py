import asyncio
import json
import uuid
from datetime import datetime, timezone

import aio_pika

AMQP_URL = "amqp://guest:guest@localhost:5672/"
EXCHANGE = "events"
ROUTING_KEY = "order.created"


async def main() -> None:
    connection = await aio_pika.connect_robust(AMQP_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
        )

        payload = {
            "order_id": str(uuid.uuid4()),
            "amount": 42.5,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
            message_id=str(uuid.uuid4()),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=ROUTING_KEY)
        print(f"Published to '{EXCHANGE}' with key '{ROUTING_KEY}': {payload}")


if __name__ == "__main__":
    asyncio.run(main())