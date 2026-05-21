from __future__ import annotations

import importlib
from typing import Any

from ...shared.config import RabbitMQSettings
from ...shared.exceptions import DependencyUnavailableError


def create_connection(settings: RabbitMQSettings) -> Any:
    try:
        pika = importlib.import_module("pika")
    except ModuleNotFoundError as exc:
        raise DependencyUnavailableError(
            "pika is required to use the RabbitMQ adapter. "
            "Install project dependencies first."
        ) from exc

    credentials = pika.PlainCredentials(settings.username, settings.password)
    parameters = pika.ConnectionParameters(
        host=settings.host,
        port=settings.port,
        virtual_host=settings.virtual_host,
        credentials=credentials,
        heartbeat=settings.heartbeat,
    )
    return pika.BlockingConnection(parameters)


def open_channel(settings: RabbitMQSettings) -> tuple[Any, Any]:
    connection = create_connection(settings)
    channel = connection.channel()
    channel.basic_qos(prefetch_count=settings.prefetch_count)
    return connection, channel
