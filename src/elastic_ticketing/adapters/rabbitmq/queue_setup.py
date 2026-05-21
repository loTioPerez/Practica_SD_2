from __future__ import annotations

from ...shared.config import RabbitMQSettings


def declare_ticket_queues(channel, settings: RabbitMQSettings) -> None:
    channel.queue_declare(queue=settings.dlq_name, durable=True)
    channel.queue_declare(
        queue=settings.queue_name,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": settings.dlq_name,
        },
    )
