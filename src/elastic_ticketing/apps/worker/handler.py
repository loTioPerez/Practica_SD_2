from __future__ import annotations

from dataclasses import asdict

from ...adapters.rabbitmq import (
    RabbitMQConsumer,
    RabbitMQPublisher,
    declare_ticket_queues,
    open_channel,
)
from ...bootstrap import build_postgres_context
from ...shared.config import RabbitMQSettings, WorkerSettings
from .worker_loop import WorkerLoop


def lambda_handler(event, context):
    del event

    rabbitmq_settings = RabbitMQSettings.from_env()
    worker_settings = WorkerSettings.from_env()
    app_context = build_postgres_context()
    connection, channel = open_channel(rabbitmq_settings)

    try:
        declare_ticket_queues(channel, rabbitmq_settings)
        consumer = RabbitMQConsumer(channel, rabbitmq_settings.queue_name)
        publisher = RabbitMQPublisher(channel, rabbitmq_settings.queue_name)
        worker_id = getattr(context, "aws_request_id", "local-worker")
        loop = WorkerLoop(
            consumer=consumer,
            purchase_service=app_context.purchase_service,
            completion_repository=app_context.completion_repository,
            publisher=publisher,
            worker_id=worker_id,
            settings=worker_settings,
        )
        return asdict(loop.run())
    finally:
        channel.close()
        connection.close()
