import asyncio
import logging
import random

logger = logging.getLogger("notification_service")


class NotificationError(Exception):
    """The notification provider failed to deliver the message."""


class NotificationSender:
    def __init__(self, latency: tuple[float, float] = (0.1, 0.4)) -> None:
        self._latency = latency

    async def send(self, customer_id: str, subject: str, body: str) -> None:
        # Simulated provider latency. A real sync SDK would be wrapped with asyncio.to_thread.
        await asyncio.sleep(random.uniform(*self._latency))
        if customer_id == "cust-notify-fail":
            raise NotificationError("email provider unavailable")
        logger.info("NOTIFICATION sent to=%s subject=%r body=%r", customer_id, subject, body)
