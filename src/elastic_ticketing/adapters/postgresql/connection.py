from __future__ import annotations

import importlib
from collections.abc import Callable, Sequence
from typing import Any

from ...shared.config import PostgresSettings
from ...shared.exceptions import DependencyUnavailableError


def create_connection(settings: PostgresSettings) -> Any:
    try:
        psycopg = importlib.import_module("psycopg")
    except ModuleNotFoundError as exc:
        raise DependencyUnavailableError(
            "psycopg is required to use the PostgreSQL adapter. "
            "Install project dependencies first."
        ) from exc

    return psycopg.connect(settings.effective_dsn)


def make_connection_factory(settings: PostgresSettings) -> Callable[[], Any]:
    return lambda: create_connection(settings)


def execute_statements(settings: PostgresSettings, statements: Sequence[str]) -> None:
    connection = create_connection(settings)
    cursor = connection.cursor()
    try:
        for statement in statements:
            cursor.execute(statement)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
