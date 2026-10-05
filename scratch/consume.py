import asyncio

import aio_pika

AMQP_URL = "amqp://guest:guest@localhost:5672/"
EXCHANGE = "events"
QUEUE = "scratch.queue"
BINDING_KEY = "order.*"


async def main() -> None:
    connection = await aio_pika.connect_robust(AMQP_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange(
            EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await channel.declare_queue(QUEUE, durable=True)
        await queue.bind(exchange, routing_key=BINDING_KEY)

        print(f"Waiting for messages on '{QUEUE}' (binding '{BINDING_KEY}'). Ctrl+C to quit.")

        async with queue.iterator() as messages:
            async for message in messages:
                # message.process() acks on success and rejects on exception
                async with message.process():
                    print(f"[{message.routing_key}] {message.body.decode()}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")