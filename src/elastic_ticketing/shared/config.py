from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from .exceptions import ConfigurationError

DEFAULT_ENV_PREFIX = "ELASTIC_TICKETING_POSTGRES_"
DEFAULT_RABBITMQ_ENV_PREFIX = "ELASTIC_TICKETING_RABBITMQ_"
DEFAULT_WORKER_ENV_PREFIX = "ELASTIC_TICKETING_WORKER_"


@dataclass(frozen=True)
class PostgresSettings:
    host: str = "localhost"
    port: int = 5432
    database: str = "elastic_ticketing"
    user: str = "postgres"
    password: str = "postgres"
    sslmode: str = "prefer"
    dsn: str | None = None

    @property
    def effective_dsn(self) -> str:
        if self.dsn:
            return self.dsn
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password} sslmode={self.sslmode}"
        )

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        prefix: str = DEFAULT_ENV_PREFIX,
    ) -> "PostgresSettings":
        values = env or os.environ
        dsn = values.get(f"{prefix}DSN")
        port_value = values.get(f"{prefix}PORT", str(cls.port))
        try:
            port = int(port_value)
        except ValueError as exc:
            raise ConfigurationError(
                f"Invalid PostgreSQL port: {port_value!r}"
            ) from exc

        return cls(
            host=values.get(f"{prefix}HOST", cls.host),
            port=port,
            database=values.get(f"{prefix}DATABASE", cls.database),
            user=values.get(f"{prefix}USER", cls.user),
            password=values.get(f"{prefix}PASSWORD", cls.password),
            sslmode=values.get(f"{prefix}SSLMODE", cls.sslmode),
            dsn=dsn,
        )


@dataclass(frozen=True)
class RabbitMQSettings:
    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"
    queue_name: str = "ticket-purchases"
    dlq_name: str = "ticket-purchases.dlq"
    prefetch_count: int = 1
    heartbeat: int = 30

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        prefix: str = DEFAULT_RABBITMQ_ENV_PREFIX,
    ) -> "RabbitMQSettings":
        values = env or os.environ
        try:
            port = int(values.get(f"{prefix}PORT", str(cls.port)))
            prefetch_count = int(
                values.get(f"{prefix}PREFETCH_COUNT", str(cls.prefetch_count))
            )
            heartbeat = int(values.get(f"{prefix}HEARTBEAT", str(cls.heartbeat)))
        except ValueError as exc:
            raise ConfigurationError(
                "RabbitMQ numeric settings must be valid integers."
            ) from exc

        return cls(
            host=values.get(f"{prefix}HOST", cls.host),
            port=port,
            username=values.get(f"{prefix}USERNAME", cls.username),
            password=values.get(f"{prefix}PASSWORD", cls.password),
            virtual_host=values.get(f"{prefix}VHOST", cls.virtual_host),
            queue_name=values.get(f"{prefix}QUEUE_NAME", cls.queue_name),
            dlq_name=values.get(f"{prefix}DLQ_NAME", cls.dlq_name),
            prefetch_count=prefetch_count,
            heartbeat=heartbeat,
        )


@dataclass(frozen=True)
class WorkerSettings:
    max_messages_per_invocation: int = 50
    max_attempts: int = 3

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        prefix: str = DEFAULT_WORKER_ENV_PREFIX,
    ) -> "WorkerSettings":
        values = env or os.environ
        try:
            max_messages = int(
                values.get(
                    f"{prefix}MAX_MESSAGES_PER_INVOCATION",
                    str(cls.max_messages_per_invocation),
                )
            )
            max_attempts = int(
                values.get(f"{prefix}MAX_ATTEMPTS", str(cls.max_attempts))
            )
        except ValueError as exc:
            raise ConfigurationError(
                "Worker numeric settings must be valid integers."
            ) from exc

        return cls(
            max_messages_per_invocation=max_messages,
            max_attempts=max_attempts,
        )
