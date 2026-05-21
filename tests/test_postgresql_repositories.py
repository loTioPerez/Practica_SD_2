from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from elastic_ticketing.adapters.postgresql.repositories import (  # noqa: E402
    PostgresCompletionRepository,
    PostgresTicketRepository,
)
from elastic_ticketing.core import (  # noqa: E402
    CompletionRecord,
    InventoryPurchaseStatus,
    PurchaseRequest,
    PurchaseStatus,
    TicketType,
)


@dataclass
class ScriptedStatement:
    sql_contains: str
    fetchone_value: object | None = None
    error: Exception | None = None


class FakeCursor:
    def __init__(self, scripted_statements: list[ScriptedStatement]) -> None:
        self._scripted_statements = list(scripted_statements)
        self._current_fetchone: object | None = None
        self.executed: list[tuple[str, object | None]] = []
        self.closed = False

    def execute(self, query: str, params: object | None = None) -> object:
        if not self._scripted_statements:
            raise AssertionError(f"Unexpected query: {query}")

        step = self._scripted_statements.pop(0)
        compact_query = " ".join(query.split())
        if step.sql_contains not in compact_query:
            raise AssertionError(
                f"Expected query containing {step.sql_contains!r}, got {compact_query!r}"
            )

        self.executed.append((compact_query, params))
        self._current_fetchone = step.fetchone_value
        if step.error is not None:
            raise step.error
        return object()

    def fetchone(self) -> object | None:
        return self._current_fetchone

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, scripted_statements: list[ScriptedStatement]) -> None:
        self.cursor_instance = FakeCursor(scripted_statements)
        self.commit_calls = 0
        self.rollback_calls = 0
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.closed = True


class PostgresTicketRepositoryTests(unittest.TestCase):
    def test_get_existing_result_maps_stored_row(self) -> None:
        connection = FakeConnection(
            [
                ScriptedStatement(
                    sql_contains="SELECT request_id, client_id, ticket_type, seat_id, status, reason",
                    fetchone_value=(
                        "req-1",
                        "client-1",
                        "numbered",
                        9,
                        "accepted",
                        None,
                    ),
                )
            ]
        )
        repository = PostgresTicketRepository(lambda: connection)

        result = repository.get_existing_result("req-1")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.request_id, "req-1")
        self.assertEqual(result.ticket_type, TicketType.NUMBERED)
        self.assertEqual(result.seat_id, 9)
        self.assertEqual(result.status, PurchaseStatus.ACCEPTED)
        self.assertEqual(connection.commit_calls, 0)
        self.assertTrue(connection.cursor_instance.closed)
        self.assertTrue(connection.closed)

    def test_purchase_unnumbered_commits_accepted_sale(self) -> None:
        connection = FakeConnection(
            [
                ScriptedStatement(
                    sql_contains="INSERT INTO purchase_requests",
                    fetchone_value=("req-1",),
                ),
                ScriptedStatement(
                    sql_contains="UPDATE unnumbered_inventory",
                    fetchone_value=(1, 1),
                ),
                ScriptedStatement(
                    sql_contains="UPDATE purchase_requests",
                ),
            ]
        )
        repository = PostgresTicketRepository(lambda: connection)
        request = PurchaseRequest(
            request_id="req-1",
            client_id="client-1",
            ticket_type=TicketType.UNNUMBERED,
        )

        outcome = repository.purchase_unnumbered(request)

        self.assertEqual(outcome.status, InventoryPurchaseStatus.PURCHASED)
        self.assertEqual(connection.commit_calls, 1)
        self.assertEqual(connection.rollback_calls, 0)
        finalize_params = connection.cursor_instance.executed[2][1]
        self.assertEqual(finalize_params[0], "accepted")

    def test_purchase_unnumbered_returns_duplicate_result(self) -> None:
        connection = FakeConnection(
            [
                ScriptedStatement(
                    sql_contains="INSERT INTO purchase_requests",
                    fetchone_value=None,
                ),
                ScriptedStatement(
                    sql_contains="SELECT request_id, client_id, ticket_type, seat_id, status, reason",
                    fetchone_value=(
                        "req-1",
                        "client-1",
                        "unnumbered",
                        None,
                        "rejected",
                        "sold_out",
                    ),
                ),
            ]
        )
        repository = PostgresTicketRepository(lambda: connection)
        request = PurchaseRequest(
            request_id="req-1",
            client_id="client-1",
            ticket_type=TicketType.UNNUMBERED,
        )

        outcome = repository.purchase_unnumbered(request)

        self.assertEqual(outcome.status, InventoryPurchaseStatus.DUPLICATE_REQUEST)
        self.assertIsNotNone(outcome.existing_result)
        assert outcome.existing_result is not None
        self.assertEqual(outcome.existing_result.status, PurchaseStatus.REJECTED)
        self.assertEqual(connection.commit_calls, 1)

    def test_purchase_numbered_conflict_returns_sold_seat_info(self) -> None:
        connection = FakeConnection(
            [
                ScriptedStatement(
                    sql_contains="INSERT INTO purchase_requests",
                    fetchone_value=("req-2",),
                ),
                ScriptedStatement(
                    sql_contains="INSERT INTO numbered_seats",
                    fetchone_value=None,
                ),
                ScriptedStatement(
                    sql_contains="SELECT seat_id, sold_to_client_id, sold_by_request_id",
                    fetchone_value=(7, "client-a", "req-a"),
                ),
                ScriptedStatement(
                    sql_contains="UPDATE purchase_requests",
                ),
            ]
        )
        repository = PostgresTicketRepository(lambda: connection)
        request = PurchaseRequest(
            request_id="req-2",
            client_id="client-2",
            ticket_type=TicketType.NUMBERED,
            seat_id=7,
        )

        outcome = repository.purchase_numbered(request)

        self.assertEqual(outcome.status, InventoryPurchaseStatus.SEAT_ALREADY_SOLD)
        self.assertIsNotNone(outcome.seat_info)
        assert outcome.seat_info is not None
        self.assertEqual(outcome.seat_info.sold_to_client_id, "client-a")
        finalize_params = connection.cursor_instance.executed[3][1]
        self.assertEqual(finalize_params[0], "rejected")
        self.assertEqual(finalize_params[1], "seat_already_sold")

    def test_purchase_rolls_back_when_database_fails(self) -> None:
        connection = FakeConnection(
            [
                ScriptedStatement(
                    sql_contains="INSERT INTO purchase_requests",
                    fetchone_value=("req-1",),
                ),
                ScriptedStatement(
                    sql_contains="UPDATE unnumbered_inventory",
                    error=RuntimeError("db down"),
                ),
            ]
        )
        repository = PostgresTicketRepository(lambda: connection)
        request = PurchaseRequest(
            request_id="req-1",
            client_id="client-1",
            ticket_type=TicketType.UNNUMBERED,
        )

        with self.assertRaisesRegex(RuntimeError, "db down"):
            repository.purchase_unnumbered(request)

        self.assertEqual(connection.commit_calls, 0)
        self.assertEqual(connection.rollback_calls, 1)
        self.assertTrue(connection.cursor_instance.closed)
        self.assertTrue(connection.closed)


class PostgresCompletionRepositoryTests(unittest.TestCase):
    def test_save_completion_upserts_and_commits(self) -> None:
        connection = FakeConnection(
            [
                ScriptedStatement(
                    sql_contains="INSERT INTO completions",
                )
            ]
        )
        repository = PostgresCompletionRepository(lambda: connection)
        record = CompletionRecord(
            request_id="req-9",
            client_id="client-9",
            ticket_type=TicketType.NUMBERED,
            status=PurchaseStatus.ACCEPTED,
            seat_id=12,
            experiment_id="exp-1",
            queued_at=datetime(2026, 5, 21, 12, 0, 0),
            started_at=datetime(2026, 5, 21, 12, 0, 1),
            completed_at=datetime(2026, 5, 21, 12, 0, 2),
            worker_id="worker-1",
            attempt=2,
        )

        repository.save_completion(record)

        self.assertEqual(connection.commit_calls, 1)
        self.assertEqual(connection.rollback_calls, 0)
        params = connection.cursor_instance.executed[0][1]
        self.assertEqual(params[0], "req-9")
        self.assertEqual(params[2], "numbered")
        self.assertEqual(params[4], "accepted")


if __name__ == "__main__":
    unittest.main()
