from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from elastic_ticketing.core import (  # noqa: E402
    InventoryPurchaseOutcome,
    InventoryPurchaseStatus,
    NumberedService,
    PurchaseRequest,
    TicketType,
    UnnumberedService,
)


class DuplicateWithoutStoredResultRepository:
    def purchase_unnumbered(
        self,
        request: PurchaseRequest,
    ) -> InventoryPurchaseOutcome:
        return InventoryPurchaseOutcome(
            status=InventoryPurchaseStatus.DUPLICATE_REQUEST,
        )

    def purchase_numbered(
        self,
        request: PurchaseRequest,
    ) -> InventoryPurchaseOutcome:
        return InventoryPurchaseOutcome(
            status=InventoryPurchaseStatus.DUPLICATE_REQUEST,
        )


class FaultToleranceContractTests(unittest.TestCase):
    def test_duplicate_unnumbered_outcome_requires_original_stored_result(self) -> None:
        service = UnnumberedService(DuplicateWithoutStoredResultRepository())
        request = PurchaseRequest(
            request_id="req-1",
            client_id="client-1",
            ticket_type=TicketType.UNNUMBERED,
        )

        with self.assertRaisesRegex(ValueError, "stored result"):
            service.buy(request)

    def test_duplicate_numbered_outcome_requires_original_stored_result(self) -> None:
        service = NumberedService(DuplicateWithoutStoredResultRepository())
        request = PurchaseRequest(
            request_id="req-1",
            client_id="client-1",
            ticket_type=TicketType.NUMBERED,
            seat_id=3,
        )

        with self.assertRaisesRegex(ValueError, "stored result"):
            service.buy(request)


if __name__ == "__main__":
    unittest.main()
