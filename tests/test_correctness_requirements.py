from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from elastic_ticketing.core import (  # noqa: E402
    IdempotencyService,
    InventoryPurchaseOutcome,
    InventoryPurchaseStatus,
    NumberedService,
    PurchaseRequest,
    PurchaseResult,
    PurchaseService,
    RejectionReason,
    RequestRepository,
    SeatInfo,
    SeatStatus,
    TicketRepository,
    TicketType,
    UnnumberedService,
    ValidationService,
)


class InMemoryTicketRepository(TicketRepository, RequestRepository):
    def __init__(self, total_tickets: int) -> None:
        self._remaining = total_tickets
        self._requests: dict[str, PurchaseResult] = {}
        self._seats: dict[int, SeatInfo] = {}

    def get_existing_result(self, request_id: str) -> PurchaseResult | None:
        return self._requests.get(request_id)

    def purchase_unnumbered(
        self,
        request: PurchaseRequest,
    ) -> InventoryPurchaseOutcome:
        existing_result = self._requests.get(request.request_id)
        if existing_result is not None:
            return InventoryPurchaseOutcome(
                status=InventoryPurchaseStatus.DUPLICATE_REQUEST,
                existing_result=existing_result,
            )

        if self._remaining <= 0:
            result = PurchaseResult.rejected_for(request, RejectionReason.SOLD_OUT)
            self._requests[request.request_id] = result
            return InventoryPurchaseOutcome(
                status=InventoryPurchaseStatus.SOLD_OUT,
            )

        self._remaining -= 1
        result = PurchaseResult.accepted_for(request)
        self._requests[request.request_id] = result
        return InventoryPurchaseOutcome(
            status=InventoryPurchaseStatus.PURCHASED,
        )

    def purchase_numbered(
        self,
        request: PurchaseRequest,
    ) -> InventoryPurchaseOutcome:
        existing_result = self._requests.get(request.request_id)
        if existing_result is not None:
            return InventoryPurchaseOutcome(
                status=InventoryPurchaseStatus.DUPLICATE_REQUEST,
                existing_result=existing_result,
            )

        assert request.seat_id is not None
        seat_info = self._seats.get(request.seat_id)
        if seat_info is not None:
            result = PurchaseResult.rejected_for(
                request,
                RejectionReason.SEAT_ALREADY_SOLD,
            )
            self._requests[request.request_id] = result
            return InventoryPurchaseOutcome(
                status=InventoryPurchaseStatus.SEAT_ALREADY_SOLD,
                seat_info=seat_info,
            )

        accepted_result = PurchaseResult.accepted_for(request)
        self._requests[request.request_id] = accepted_result
        self._seats[request.seat_id] = SeatInfo(
            seat_id=request.seat_id,
            status=SeatStatus.SOLD,
            sold_to_client_id=request.client_id,
            sold_by_request_id=request.request_id,
        )
        return InventoryPurchaseOutcome(
            status=InventoryPurchaseStatus.PURCHASED,
            seat_info=self._seats[request.seat_id],
        )

    def get_seat(self, seat_id: int) -> SeatInfo | None:
        return self._seats.get(seat_id)


class StaleRequestRepository(RequestRepository):
    def get_existing_result(self, request_id: str) -> PurchaseResult | None:
        return None


def build_purchase_service(
    *,
    total_tickets: int = 100_000,
    ticket_repository: TicketRepository | None = None,
    request_repository: RequestRepository | None = None,
) -> PurchaseService:
    repository = ticket_repository or InMemoryTicketRepository(total_tickets)
    return PurchaseService(
        validation_service=ValidationService(total_tickets=total_tickets),
        idempotency_service=IdempotencyService(
            request_repository=request_repository or repository
        ),
        numbered_service=NumberedService(repository),
        unnumbered_service=UnnumberedService(repository),
    )


class ValidationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ValidationService(total_tickets=3)

    def test_rejects_missing_seat_for_numbered_purchase(self) -> None:
        request = PurchaseRequest(
            request_id="req-1",
            client_id="client-1",
            ticket_type=TicketType.NUMBERED,
        )

        result = self.service.validate(request)

        self.assertEqual(result, RejectionReason.MISSING_SEAT_ID)

    def test_rejects_unexpected_seat_for_unnumbered_purchase(self) -> None:
        request = PurchaseRequest(
            request_id="req-1",
            client_id="client-1",
            ticket_type=TicketType.UNNUMBERED,
            seat_id=1,
        )

        result = self.service.validate(request)

        self.assertEqual(result, RejectionReason.UNEXPECTED_SEAT_ID)

    def test_rejects_invalid_seat_id_out_of_range(self) -> None:
        request = PurchaseRequest(
            request_id="req-1",
            client_id="client-1",
            ticket_type=TicketType.NUMBERED,
            seat_id=4,
        )

        result = self.service.validate(request)

        self.assertEqual(result, RejectionReason.INVALID_SEAT_ID)

    def test_rejects_non_enum_ticket_type(self) -> None:
        request = PurchaseRequest(
            request_id="req-1",
            client_id="client-1",
            ticket_type="numbered",  # type: ignore[arg-type]
            seat_id=1,
        )

        result = self.service.validate(request)

        self.assertEqual(result, RejectionReason.INVALID_TICKET_TYPE)


class PurchaseCorrectnessTests(unittest.TestCase):
    def test_unnumbered_sales_stop_exactly_at_capacity(self) -> None:
        service = build_purchase_service(total_tickets=2)

        first = service.buy_unnumbered("req-1", "client-1")
        second = service.buy_unnumbered("req-2", "client-2")
        third = service.buy_unnumbered("req-3", "client-3")

        self.assertEqual(first.status.value, "accepted")
        self.assertEqual(second.status.value, "accepted")
        self.assertEqual(third.status.value, "rejected")
        self.assertEqual(third.reason, RejectionReason.SOLD_OUT)

    def test_numbered_seat_can_be_sold_only_once(self) -> None:
        service = build_purchase_service(total_tickets=5)

        accepted = service.buy_numbered("req-1", "client-1", seat_id=2)
        rejected = service.buy_numbered("req-2", "client-2", seat_id=2)

        self.assertEqual(accepted.status.value, "accepted")
        self.assertEqual(rejected.status.value, "rejected")
        self.assertEqual(rejected.reason, RejectionReason.SEAT_ALREADY_SOLD)

    def test_duplicate_request_returns_same_stored_result_from_precheck(self) -> None:
        repository = InMemoryTicketRepository(total_tickets=1)
        service = build_purchase_service(total_tickets=1, ticket_repository=repository)

        first = service.buy_unnumbered("req-1", "client-1")
        repeated = service.buy_unnumbered("req-1", "client-1")

        self.assertEqual(first, repeated)

    def test_duplicate_request_returns_same_result_when_repository_detects_it(self) -> None:
        repository = InMemoryTicketRepository(total_tickets=1)
        service = build_purchase_service(
            total_tickets=1,
            ticket_repository=repository,
            request_repository=StaleRequestRepository(),
        )

        first = service.buy_unnumbered("req-1", "client-1")
        repeated = service.buy_unnumbered("req-1", "client-1")

        self.assertEqual(first, repeated)


if __name__ == "__main__":
    unittest.main()
