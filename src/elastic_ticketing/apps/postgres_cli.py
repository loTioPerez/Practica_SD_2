from __future__ import annotations

import argparse
from dataclasses import asdict
from pprint import pprint

from ..adapters.postgresql.connection import execute_statements
from ..adapters.postgresql.schema import (
    create_schema_sql,
    drop_schema_sql,
    reset_schema_sql,
)
from ..bootstrap import build_postgres_context
from ..shared.config import PostgresSettings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Small PostgreSQL utility CLI for elastic ticketing."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Create schema tables.")
    init_parser.add_argument(
        "--initial-unnumbered-tickets",
        type=int,
        default=100_000,
        help="Initial stock for unnumbered tickets.",
    )

    reset_parser = subparsers.add_parser("reset-db", help="Reset schema contents.")
    reset_parser.add_argument(
        "--initial-unnumbered-tickets",
        type=int,
        default=100_000,
        help="Initial stock for unnumbered tickets after reset.",
    )

    subparsers.add_parser("drop-db", help="Drop schema tables.")

    unnumbered_parser = subparsers.add_parser(
        "buy-unnumbered",
        help="Execute one unnumbered purchase.",
    )
    _add_common_purchase_args(unnumbered_parser)

    numbered_parser = subparsers.add_parser(
        "buy-numbered",
        help="Execute one numbered purchase.",
    )
    _add_common_purchase_args(numbered_parser)
    numbered_parser.add_argument("--seat-id", type=int, required=True)

    request_parser = subparsers.add_parser(
        "show-request",
        help="Show stored result for a request_id.",
    )
    request_parser.add_argument("--request-id", required=True)

    seat_parser = subparsers.add_parser(
        "show-seat",
        help="Show current information for a numbered seat.",
    )
    seat_parser.add_argument("--seat-id", type=int, required=True)

    return parser


def _add_common_purchase_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--experiment-id")


def _run_schema_action(action: str, args: argparse.Namespace) -> None:
    settings = PostgresSettings.from_env()
    if action == "init-db":
        execute_statements(
            settings,
            create_schema_sql(args.initial_unnumbered_tickets),
        )
    elif action == "reset-db":
        execute_statements(
            settings,
            create_schema_sql(args.initial_unnumbered_tickets),
        )
        execute_statements(
            settings,
            reset_schema_sql(args.initial_unnumbered_tickets),
        )
    else:
        execute_statements(settings, drop_schema_sql())


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command in {"init-db", "reset-db", "drop-db"}:
        _run_schema_action(args.command, args)
        return

    context = build_postgres_context()
    if args.command == "buy-unnumbered":
        result = context.purchase_service.buy_unnumbered(
            request_id=args.request_id,
            client_id=args.client_id,
            experiment_id=args.experiment_id,
        )
        pprint(asdict(result))
        return

    if args.command == "buy-numbered":
        result = context.purchase_service.buy_numbered(
            request_id=args.request_id,
            client_id=args.client_id,
            seat_id=args.seat_id,
            experiment_id=args.experiment_id,
        )
        pprint(asdict(result))
        return

    if args.command == "show-request":
        result = context.ticket_repository.get_existing_result(args.request_id)
        pprint(asdict(result) if result is not None else None)
        return

    seat_info = context.ticket_repository.get_seat(args.seat_id)
    pprint(asdict(seat_info) if seat_info is not None else None)


if __name__ == "__main__":
    main()
