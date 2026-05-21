from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from elastic_ticketing.adapters.postgresql.connection import (  # noqa: E402
    create_connection,
    execute_statements,
)
from elastic_ticketing.adapters.postgresql.schema import (  # noqa: E402
    COMPLETIONS_TABLE,
    create_schema_sql,
    reset_schema_sql,
)
from elastic_ticketing.bootstrap import build_postgres_context  # noqa: E402
from elastic_ticketing.core import CompletionRecord, PurchaseStatus, TicketType  # noqa: E402
from elastic_ticketing.shared.config import PostgresSettings  # noqa: E402


class PostgresIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        dsn = os.environ.get("ELASTIC_TICKETING_POSTGRES_TEST_DSN", "").strip()
        if not dsn:
            raise unittest.SkipTest("ELASTIC_TICKETING_POSTGRES_TEST_DSN is not set.")

        if importlib.util.find_spec("psycopg") is None:
            raise unittest.SkipTest("psycopg is not installed.")

        cls.settings = PostgresSettings(dsn=dsn)
        execute_statements(cls.settings, create_schema_sql(initial_unnumbered_tickets=2))

    def setUp(self) -> None:
        execute_statements(self.settings, reset_schema_sql(initial_unnumbered_tickets=2))
        self.context = build_postgres_context(self.settings)

    def test_unnumbered_sales_stop_at_capacity_in_real_postgres(self) -> None:
        first = self.context.purchase_service.buy_unnumbered("req-1", "client-1")
        second = self.context.purchase_service.buy_unnumbered("req-2", "client-2")
        third = self.context.purchase_service.buy_unnumbered("req-3", "client-3")

        self.assertEqual(first.status.value, "accepted")
        self.assertEqual(second.status.value, "accepted")
        self.assertEqual(third.status.value, "rejected")
        self.assertEqual(third.reason.value, "sold_out")

    def test_numbered_conflict_and_duplicate_request_in_real_postgres(self) -> None:
        accepted = self.context.purchase_service.buy_numbered(
            "req-10",
            "client-10",
            seat_id=7,
        )
        duplicate = self.context.purchase_service.buy_numbered(
            "req-10",
            "client-10",
            seat_id=7,
        )
        conflict = self.context.purchase_service.buy_numbered(
            "req-11",
            "client-11",
            seat_id=7,
        )

        self.assertEqual(accepted.status.value, "accepted")
        self.assertEqual(duplicate, accepted)
        self.assertEqual(conflict.status.value, "rejected")
        self.assertEqual(conflict.reason.value, "seat_already_sold")

    def test_completion_repository_saves_records_in_real_postgres(self) -> None:
        record = CompletionRecord(
            request_id="req-90",
            client_id="client-90",
            ticket_type=TicketType.UNNUMBERED,
            status=PurchaseStatus.ACCEPTED,
            completed_at=datetime(2026, 5, 21, 18, 0, 0),
            attempt=1,
        )

        self.context.completion_repository.save_completion(record)

        connection = create_connection(self.settings)
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT request_id, client_id, ticket_type, status, attempt
                FROM {COMPLETIONS_TABLE}
                WHERE request_id = %s
                """,
                ("req-90",),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
            connection.close()

        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row[0], "req-90")
        self.assertEqual(row[1], "client-90")
        self.assertEqual(row[2], "unnumbered")
        self.assertEqual(row[3], "accepted")
        self.assertEqual(row[4], 1)


if __name__ == "__main__":
    unittest.main()
