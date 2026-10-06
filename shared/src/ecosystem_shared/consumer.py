"""Reusable background consumer: decode, dedup, basic retry, ack/reject."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage, AbstractQueue

from ecosystem_shared.broker import BrokerClient
from ecosystem_shared.constants import EXCHANGE_NAME
from ecosystem_shared.events import EVENT_REGISTRY, BaseEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[BaseEvent], Awaitable[None]]


class InMemoryDedupStore:
    """Remembers processed event ids. Lost on restart; Phase 9 improves this."""

    def __init__(self) -> None:
        self._seen: set[UUID] = set()

    def seen(self, event_id: UUID) -> bool:
        return event_id in self._seen

    def mark(self, event_id: UUID) -> None:
        self._seen.add(event_id)


class EventConsumer:
    def __init__(
        self,
        broker: BrokerClient,
        queue_name: str,
        binding_keys: list[str],
        handler: EventHandler,
        *,
        max_attempts: int = 3,
        base_delay: float = 0.5,
        prefetch: int = 1,
        dedup: InMemoryDedupStore | None = None,
    ) -> None:
        self._broker = broker
        self._queue_name = queue_name
        self._binding_keys = binding_keys
        self._handler = handler
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._prefetch = prefetch
        self._dedup = dedup or InMemoryDedupStore()
        self._channel: AbstractChannel | None = None
        self._queue: AbstractQueue | None = None
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        # A dedicated channel for consuming, separate from the publishing channel.
        self._channel = await self._broker.new_channel()
        await self._channel.set_qos(prefetch_count=self._prefetch)
        exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )
        self._queue = await self._channel.declare_queue(self._queue_name, durable=True)
        for key in self._binding_keys:
            await self._queue.bind(exchange, routing_key=key)

        self._task = asyncio.create_task(self._run(), name=f"consumer:{self._queue_name}")
        self._task.add_done_callback(self._on_done)
        logger.info("consumer started queue=%s bindings=%s", self._queue_name, self._binding_keys)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("consumer task ended with an error")
            self._task = None
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
        logger.info("consumer stopped queue=%s", self._queue_name)

    def _on_done(self, task: asyncio.Task[None]) -> None:
        if not task.cancelled() and task.exception() is not None:
            logger.error("consumer task crashed", exc_info=task.exception())

    async def _run(self) -> None:
        assert self._queue is not None
        async with self._queue.iterator() as messages:
            async for message in messages:
                await self.handle_message(message)

    @staticmethod
    def _decode(message: AbstractIncomingMessage) -> BaseEvent:
        key = message.type or message.routing_key
        event_cls = EVENT_REGISTRY.get(key) if key else None
        if event_cls is None:
            raise ValueError(f"unknown event type: {key!r}")
        return event_cls.model_validate_json(message.body)

    async def handle_message(self, message: AbstractIncomingMessage) -> None:
        try:
            event = self._decode(message)
        except Exception:
            logger.exception("undecodable message; rejecting without requeue")
            await message.reject(requeue=False)
            return

        if self._dedup.seen(event.event_id):
            logger.info(
                "duplicate event skipped event_id=%s type=%s", event.event_id, event.event_type
            )
            await message.ack()
            return

        for attempt in range(1, self._max_attempts + 1):
            try:
                logger.info(
                    "handling event type=%s event_id=%s correlation_id=%s attempt=%d",
                    event.event_type,
                    event.event_id,
                    event.correlation_id,
                    attempt,
                )
                await self._handler(event)
            except Exception:
                if attempt == self._max_attempts:
                    logger.exception(
                        "giving up on event_id=%s after %d attempts", event.event_id, attempt
                    )
                    await message.reject(
                        requeue=False
                    )  # dropped until Phase 9 adds a dead-letter queue
                    return
                delay = self._base_delay * 2 ** (attempt - 1)
                logger.warning(
                    "attempt %d failed for event_id=%s; retrying in %.1fs",
                    attempt,
                    event.event_id,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                self._dedup.mark(event.event_id)
                await message.ack()
                return
