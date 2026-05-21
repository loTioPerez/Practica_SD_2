from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from .exceptions import ConfigurationError

DEFAULT_ENV_PREFIX = "ELASTIC_TICKETING_POSTGRES_"


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
