from __future__ import annotations

import argparse
from collections.abc import Sequence

from ...shared.constants import TOTAL_TICKETS

PURCHASE_REQUESTS_TABLE = "purchase_requests"
UNNUMBERED_INVENTORY_TABLE = "unnumbered_inventory"
NUMBERED_SEATS_TABLE = "numbered_seats"
COMPLETIONS_TABLE = "completions"


def create_schema_sql(
    initial_unnumbered_tickets: int = TOTAL_TICKETS,
) -> list[str]:
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {PURCHASE_REQUESTS_TABLE} (
            request_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            ticket_type TEXT NOT NULL,
            seat_id INTEGER NULL,
            experiment_id TEXT NULL,
            status TEXT NOT NULL CHECK (status IN ('processing', 'accepted', 'rejected')),
            reason TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """.strip(),
        f"""
        CREATE TABLE IF NOT EXISTS {UNNUMBERED_INVENTORY_TABLE} (
            inventory_id SMALLINT PRIMARY KEY,
            remaining_count INTEGER NOT NULL CHECK (remaining_count >= 0),
            sold_count INTEGER NOT NULL CHECK (sold_count >= 0)
        )
        """.strip(),
        f"""
        CREATE TABLE IF NOT EXISTS {NUMBERED_SEATS_TABLE} (
            seat_id INTEGER PRIMARY KEY CHECK (seat_id > 0),
            sold_to_client_id TEXT NOT NULL,
            sold_by_request_id TEXT NOT NULL UNIQUE,
            sold_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """.strip(),
        f"""
        CREATE TABLE IF NOT EXISTS {COMPLETIONS_TABLE} (
            request_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            ticket_type TEXT NOT NULL,
            seat_id INTEGER NULL,
            status TEXT NOT NULL,
            reason TEXT NULL,
            experiment_id TEXT NULL,
            queued_at TIMESTAMPTZ NULL,
            started_at TIMESTAMPTZ NULL,
            completed_at TIMESTAMPTZ NULL,
            worker_id TEXT NULL,
            attempt INTEGER NOT NULL DEFAULT 1 CHECK (attempt >= 1),
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """.strip(),
        f"""
        INSERT INTO {UNNUMBERED_INVENTORY_TABLE} (
            inventory_id,
            remaining_count,
            sold_count
        ) VALUES (1, {initial_unnumbered_tickets}, 0)
        ON CONFLICT (inventory_id) DO NOTHING
        """.strip(),
    ]


def reset_schema_sql(
    initial_unnumbered_tickets: int = TOTAL_TICKETS,
) -> list[str]:
    return [
        f"TRUNCATE TABLE {COMPLETIONS_TABLE}",
        f"TRUNCATE TABLE {NUMBERED_SEATS_TABLE}",
        f"TRUNCATE TABLE {PURCHASE_REQUESTS_TABLE}",
        f"DELETE FROM {UNNUMBERED_INVENTORY_TABLE} WHERE inventory_id = 1",
        f"""
        INSERT INTO {UNNUMBERED_INVENTORY_TABLE} (
            inventory_id,
            remaining_count,
            sold_count
        ) VALUES (1, {initial_unnumbered_tickets}, 0)
        """.strip(),
    ]


def drop_schema_sql() -> list[str]:
    return [
        f"DROP TABLE IF EXISTS {COMPLETIONS_TABLE}",
        f"DROP TABLE IF EXISTS {NUMBERED_SEATS_TABLE}",
        f"DROP TABLE IF EXISTS {PURCHASE_REQUESTS_TABLE}",
        f"DROP TABLE IF EXISTS {UNNUMBERED_INVENTORY_TABLE}",
    ]


def render_sql(statements: Sequence[str]) -> str:
    return ";\n\n".join(statement.strip() for statement in statements) + ";\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render SQL for the elastic ticketing PostgreSQL schema."
    )
    parser.add_argument(
        "action",
        choices=("create", "reset", "drop"),
        help="Which SQL bundle to print.",
    )
    parser.add_argument(
        "--initial-unnumbered-tickets",
        type=int,
        default=TOTAL_TICKETS,
        help="Initial stock used when creating or resetting the schema.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.action == "create":
        sql = render_sql(create_schema_sql(args.initial_unnumbered_tickets))
    elif args.action == "reset":
        sql = render_sql(reset_schema_sql(args.initial_unnumbered_tickets))
    else:
        sql = render_sql(drop_schema_sql())
    print(sql, end="")


if __name__ == "__main__":
    main()
