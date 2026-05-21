from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RabbitMQDelivery:
    body: bytes
    delivery_tag: int
    redelivered: bool


class RabbitMQConsumer:
    def __init__(self, channel, queue_name: str) -> None:
        self._channel = channel
        self._queue_name = queue_name

    def get_message(self) -> RabbitMQDelivery | None:
        method_frame, _, body = self._channel.basic_get(
            queue=self._queue_name,
            auto_ack=False,
        )
        if method_frame is None:
            return None
        return RabbitMQDelivery(
            body=body,
            delivery_tag=method_frame.delivery_tag,
            redelivered=bool(method_frame.redelivered),
        )

    def ack(self, delivery: RabbitMQDelivery) -> None:
        self._channel.basic_ack(delivery.delivery_tag)

    def reject(self, delivery: RabbitMQDelivery, *, requeue: bool = False) -> None:
        self._channel.basic_reject(delivery.delivery_tag, requeue=requeue)
