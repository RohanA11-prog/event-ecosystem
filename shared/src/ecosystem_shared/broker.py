"""A small async RabbitMQ client that every service reuses."""

import aio_pika
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractRobustConnection,
)

from ecosystem_shared.constants import EXCHANGE_NAME
from ecosystem_shared.events import BaseEvent


class BrokerClient:
    def __init__(self, url: str) -> None:
        self._url = url
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange: AbstractExchange | None = None

    async def connect(self) -> None:
        # connect_robust reconnects automatically if the broker restarts.
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
        self._connection = self._channel = self._exchange = None

    async def new_channel(self) -> AbstractChannel:
        """Open a separate channel (consumers should not share the publishing channel)."""
        if self._connection is None:
            raise RuntimeError("BrokerClient is not connected; call connect() first")
        return await self._connection.channel()

    @property
    def channel(self) -> AbstractChannel:
        if self._channel is None:
            raise RuntimeError("BrokerClient is not connected; call connect() first")
        return self._channel

    @property
    def exchange(self) -> AbstractExchange:
        if self._exchange is None:
            raise RuntimeError("BrokerClient is not connected; call connect() first")
        return self._exchange

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and not self._connection.is_closed

    async def publish(self, event: BaseEvent) -> None:
        message = aio_pika.Message(
            body=event.model_dump_json().encode(),
            content_type="application/json",
            message_id=str(event.event_id),
            correlation_id=str(event.correlation_id),
            type=event.event_type,
            timestamp=event.occurred_at,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self.exchange.publish(message, routing_key=event.event_type)
