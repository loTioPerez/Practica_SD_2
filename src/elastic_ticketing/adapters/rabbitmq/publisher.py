from __future__ import annotations

import importlib
from datetime import datetime

from ...core import PurchaseRequest
from .serializer import QueueMessage, serialize_queue_message


def _build_basic_properties():
    try:
        pika = importlib.import_module("pika")
    except ModuleNotFoundError:
        return None
    return pika.BasicProperties(
        content_type="application/json",
        delivery_mode=2,
    )


class RabbitMQPublisher:
    def __init__(self, channel, queue_name: str) -> None:
        self._channel = channel
        self._queue_name = queue_name

    def publish_message(self, message: QueueMessage) -> None:
        self._channel.basic_publish(
            exchange="",
            routing_key=self._queue_name,
            body=serialize_queue_message(message),
            properties=_build_basic_properties(),
        )

    def publish_purchase_request(
        self,
        request: PurchaseRequest,
        *,
        queued_at: datetime | None = None,
        attempt: int = 1,
    ) -> None:
        self.publish_message(
            QueueMessage.from_purchase_request(
                request,
                queued_at=queued_at,
                attempt=attempt,
            )
        )

    def publish_quit(self) -> None:
        self.publish_message(QueueMessage.quit())
