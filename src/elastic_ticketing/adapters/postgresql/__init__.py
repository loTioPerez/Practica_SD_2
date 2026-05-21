__all__ = [
    "COMPLETIONS_TABLE",
    "NUMBERED_SEATS_TABLE",
    "PURCHASE_REQUESTS_TABLE",
    "PostgresCompletionRepository",
    "PostgresTicketRepository",
    "UNNUMBERED_INVENTORY_TABLE",
    "create_connection",
    "execute_statements",
    "create_schema_sql",
    "drop_schema_sql",
    "make_connection_factory",
    "reset_schema_sql",
]


def __getattr__(name: str):
    if name in {"create_connection", "execute_statements", "make_connection_factory"}:
        from .connection import (
            create_connection,
            execute_statements,
            make_connection_factory,
        )

        return {
            "create_connection": create_connection,
            "execute_statements": execute_statements,
            "make_connection_factory": make_connection_factory,
        }[name]

    if name in {"PostgresCompletionRepository", "PostgresTicketRepository"}:
        from .repositories import (
            PostgresCompletionRepository,
            PostgresTicketRepository,
        )

        return {
            "PostgresCompletionRepository": PostgresCompletionRepository,
            "PostgresTicketRepository": PostgresTicketRepository,
        }[name]

    if name in {
        "COMPLETIONS_TABLE",
        "NUMBERED_SEATS_TABLE",
        "PURCHASE_REQUESTS_TABLE",
        "UNNUMBERED_INVENTORY_TABLE",
        "create_schema_sql",
        "drop_schema_sql",
        "reset_schema_sql",
    }:
        from .schema import (
            COMPLETIONS_TABLE,
            NUMBERED_SEATS_TABLE,
            PURCHASE_REQUESTS_TABLE,
            UNNUMBERED_INVENTORY_TABLE,
            create_schema_sql,
            drop_schema_sql,
            reset_schema_sql,
        )

        return {
            "COMPLETIONS_TABLE": COMPLETIONS_TABLE,
            "NUMBERED_SEATS_TABLE": NUMBERED_SEATS_TABLE,
            "PURCHASE_REQUESTS_TABLE": PURCHASE_REQUESTS_TABLE,
            "UNNUMBERED_INVENTORY_TABLE": UNNUMBERED_INVENTORY_TABLE,
            "create_schema_sql": create_schema_sql,
            "drop_schema_sql": drop_schema_sql,
            "reset_schema_sql": reset_schema_sql,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
