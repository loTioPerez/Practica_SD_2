from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ...shared.config import PostgresSettings
from ...shared.exceptions import DependencyUnavailableError


def create_connection(settings: PostgresSettings) -> Any:
    try:
        import psycopg
    except ModuleNotFoundError as exc:
        raise DependencyUnavailableError(
            "psycopg is required to use the PostgreSQL adapter. "
            "Install project dependencies first."
        ) from exc

    return psycopg.connect(settings.effective_dsn)


def make_connection_factory(settings: PostgresSettings) -> Callable[[], Any]:
    return lambda: create_connection(settings)
