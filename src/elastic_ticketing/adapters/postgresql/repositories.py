from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, Protocol, TypeAlias

from ...core.domain import (
    CompletionRecord,
    InventoryPurchaseOutcome,
    InventoryPurchaseStatus,
    PurchaseRequest,
    PurchaseResult,
    PurchaseStatus,
    RejectionReason,
    SeatInfo,
    SeatStatus,
    TicketType,
)
from ...core.ports import CompletionRepository, RequestRepository, TicketRepository
from ...shared.exceptions import PersistenceError
from .schema import (
    COMPLETIONS_TABLE,
    NUMBERED_SEATS_TABLE,
    PURCHASE_REQUESTS_TABLE,
    UNNUMBERED_INVENTORY_TABLE,
)

PROCESSING_STATUS = "processing"


class CursorLike(Protocol):
    def execute(
        self,
        query: str,
        params: Sequence[object] | None = None,
    ) -> object: ...

    def fetchone(self) -> Any: ...

    def close(self) -> None: ...


class ConnectionLike(Protocol):
    def cursor(self) -> CursorLike: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


ConnectionFactory: TypeAlias = Callable[[], ConnectionLike]


class PostgresTicketRepository(TicketRepository, RequestRepository):
    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def get_existing_result(self, request_id: str) -> PurchaseResult | None:
        def operation(cursor: CursorLike) -> PurchaseResult | None:
            return self._load_existing_result(cursor, request_id)

        return self._run(operation, transactional=False)

    def purchase_unnumbered(
        self,
        request: PurchaseRequest,
    ) -> InventoryPurchaseOutcome:
        def operation(cursor: CursorLike) -> InventoryPurchaseOutcome:
            if not self._claim_request(cursor, request):
                existing_result = self._load_existing_result(cursor, request.request_id)
                if existing_result is None:
                    raise PersistenceError(
                        "Duplicate request detected for unnumbered purchase, "
                        "but no stored result could be loaded."
                    )
                return InventoryPurchaseOutcome(
                    status=InventoryPurchaseStatus.DUPLICATE_REQUEST,
                    existing_result=existing_result,
                )

            cursor.execute(
                f"""
                UPDATE {UNNUMBERED_INVENTORY_TABLE}
                SET remaining_count = remaining_count - 1,
                    sold_count = sold_count + 1
                WHERE inventory_id = 1 AND remaining_count > 0
                RETURNING remaining_count, sold_count
                """,
            )
            inventory_row = cursor.fetchone()
            if inventory_row is None:
                result = PurchaseResult.rejected_for(request, RejectionReason.SOLD_OUT)
                self._finalize_request(cursor, result)
                return InventoryPurchaseOutcome(
                    status=InventoryPurchaseStatus.SOLD_OUT,
                )

            self._finalize_request(cursor, PurchaseResult.accepted_for(request))
            return InventoryPurchaseOutcome(
                status=InventoryPurchaseStatus.PURCHASED,
            )

        return self._run(operation, transactional=True)

    def purchase_numbered(
        self,
        request: PurchaseRequest,
    ) -> InventoryPurchaseOutcome:
        def operation(cursor: CursorLike) -> InventoryPurchaseOutcome:
            if not self._claim_request(cursor, request):
                existing_result = self._load_existing_result(cursor, request.request_id)
                if existing_result is None:
                    raise PersistenceError(
                        "Duplicate request detected for numbered purchase, "
                        "but no stored result could be loaded."
                    )
                return InventoryPurchaseOutcome(
                    status=InventoryPurchaseStatus.DUPLICATE_REQUEST,
                    existing_result=existing_result,
                )

            cursor.execute(
                f"""
                INSERT INTO {NUMBERED_SEATS_TABLE} (
                    seat_id,
                    sold_to_client_id,
                    sold_by_request_id
                ) VALUES (%s, %s, %s)
                ON CONFLICT (seat_id) DO NOTHING
                RETURNING seat_id, sold_to_client_id, sold_by_request_id
                """,
                (request.seat_id, request.client_id, request.request_id),
            )
            inserted_row = cursor.fetchone()
            if inserted_row is not None:
                seat_info = self._map_sold_seat_row(inserted_row)
                self._finalize_request(cursor, PurchaseResult.accepted_for(request))
                return InventoryPurchaseOutcome(
                    status=InventoryPurchaseStatus.PURCHASED,
                    seat_info=seat_info,
                )

            if request.seat_id is None:
                raise PersistenceError(
                    "Numbered purchases require a seat_id before reaching persistence."
                )

            seat_info = self._load_seat_info(cursor, request.seat_id)
            self._finalize_request(
                cursor,
                PurchaseResult.rejected_for(
                    request,
                    RejectionReason.SEAT_ALREADY_SOLD,
                ),
            )
            return InventoryPurchaseOutcome(
                status=InventoryPurchaseStatus.SEAT_ALREADY_SOLD,
                seat_info=seat_info,
            )

        return self._run(operation, transactional=True)

    def get_seat(self, seat_id: int) -> SeatInfo | None:
        def operation(cursor: CursorLike) -> SeatInfo | None:
            cursor.execute(
                f"""
                SELECT seat_id, sold_to_client_id, sold_by_request_id
                FROM {NUMBERED_SEATS_TABLE}
                WHERE seat_id = %s
                """,
                (seat_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._map_sold_seat_row(row)

        return self._run(operation, transactional=False)

    def _run(
        self,
        operation: Callable[[CursorLike], Any],
        *,
        transactional: bool,
    ) -> Any:
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            result = operation(cursor)
            if transactional:
                connection.commit()
            return result
        except Exception:
            if transactional:
                connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def _claim_request(
        self,
        cursor: CursorLike,
        request: PurchaseRequest,
    ) -> bool:
        cursor.execute(
            f"""
            INSERT INTO {PURCHASE_REQUESTS_TABLE} (
                request_id,
                client_id,
                ticket_type,
                seat_id,
                experiment_id,
                status,
                reason
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (request_id) DO NOTHING
            RETURNING request_id
            """,
            (
                request.request_id,
                request.client_id,
                request.ticket_type.value,
                request.seat_id,
                request.experiment_id,
                PROCESSING_STATUS,
                None,
            ),
        )
        return cursor.fetchone() is not None

    def _finalize_request(
        self,
        cursor: CursorLike,
        result: PurchaseResult,
    ) -> None:
        cursor.execute(
            f"""
            UPDATE {PURCHASE_REQUESTS_TABLE}
            SET status = %s,
                reason = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE request_id = %s
            """,
            (
                result.status.value,
                result.reason.value if result.reason is not None else None,
                result.request_id,
            ),
        )

    def _load_existing_result(
        self,
        cursor: CursorLike,
        request_id: str,
    ) -> PurchaseResult | None:
        cursor.execute(
            f"""
            SELECT request_id, client_id, ticket_type, seat_id, status, reason
            FROM {PURCHASE_REQUESTS_TABLE}
            WHERE request_id = %s
            """,
            (request_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._map_request_row(row)

    def _load_seat_info(
        self,
        cursor: CursorLike,
        seat_id: int,
    ) -> SeatInfo:
        cursor.execute(
            f"""
            SELECT seat_id, sold_to_client_id, sold_by_request_id
            FROM {NUMBERED_SEATS_TABLE}
            WHERE seat_id = %s
            """,
            (seat_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise PersistenceError(
                "Seat conflict detected, but the stored sold seat row could not be loaded."
            )
        return self._map_sold_seat_row(row)

    def _map_request_row(self, row: Sequence[object]) -> PurchaseResult:
        try:
            ticket_type = TicketType(str(row[2]))
            status = PurchaseStatus(str(row[4]))
        except ValueError as exc:
            raise PersistenceError(
                f"Stored request row has unsupported enum values: {row!r}"
            ) from exc

        reason_value = row[5]
        reason = RejectionReason(str(reason_value)) if reason_value is not None else None
        return PurchaseResult(
            request_id=str(row[0]),
            client_id=str(row[1]),
            ticket_type=ticket_type,
            seat_id=int(row[3]) if row[3] is not None else None,
            status=status,
            reason=reason,
        )

    def _map_sold_seat_row(self, row: Sequence[object]) -> SeatInfo:
        return SeatInfo(
            seat_id=int(row[0]),
            status=SeatStatus.SOLD,
            sold_to_client_id=str(row[1]),
            sold_by_request_id=str(row[2]),
        )


class PostgresCompletionRepository(CompletionRepository):
    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def save_completion(self, record: CompletionRecord) -> None:
        def operation(cursor: CursorLike) -> None:
            cursor.execute(
                f"""
                INSERT INTO {COMPLETIONS_TABLE} (
                    request_id,
                    client_id,
                    ticket_type,
                    seat_id,
                    status,
                    reason,
                    experiment_id,
                    queued_at,
                    started_at,
                    completed_at,
                    worker_id,
                    attempt
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (request_id) DO UPDATE
                SET client_id = EXCLUDED.client_id,
                    ticket_type = EXCLUDED.ticket_type,
                    seat_id = EXCLUDED.seat_id,
                    status = EXCLUDED.status,
                    reason = EXCLUDED.reason,
                    experiment_id = EXCLUDED.experiment_id,
                    queued_at = EXCLUDED.queued_at,
                    started_at = EXCLUDED.started_at,
                    completed_at = EXCLUDED.completed_at,
                    worker_id = EXCLUDED.worker_id,
                    attempt = EXCLUDED.attempt,
                    recorded_at = CURRENT_TIMESTAMP
                """,
                self._completion_params(record),
            )

        self._run(operation)

    def _run(self, operation: Callable[[CursorLike], None]) -> None:
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            operation(cursor)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def _completion_params(self, record: CompletionRecord) -> tuple[object, ...]:
        return (
            record.request_id,
            record.client_id,
            record.ticket_type.value,
            record.seat_id,
            record.status.value,
            record.reason.value if record.reason is not None else None,
            record.experiment_id,
            self._optional_datetime(record.queued_at),
            self._optional_datetime(record.started_at),
            self._optional_datetime(record.completed_at),
            record.worker_id,
            record.attempt,
        )

    def _optional_datetime(self, value: datetime | None) -> datetime | None:
        return value
