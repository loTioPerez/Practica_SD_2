from __future__ import annotations

from ..domain.enums import InventoryPurchaseStatus, RejectionReason
from ..domain.models import PurchaseRequest, PurchaseResult
from ..ports import TicketRepository


class UnnumberedService:
    def __init__(self, ticket_repository: TicketRepository) -> None:
        self._ticket_repository = ticket_repository

    def buy(self, request: PurchaseRequest) -> PurchaseResult:
        outcome = self._ticket_repository.purchase_unnumbered(request)

        if outcome.status is InventoryPurchaseStatus.PURCHASED:
            return PurchaseResult.accepted_for(request)

        if outcome.status is InventoryPurchaseStatus.SOLD_OUT:
            return PurchaseResult.rejected_for(request, RejectionReason.SOLD_OUT)

        if outcome.status is InventoryPurchaseStatus.DUPLICATE_REQUEST:
            if outcome.existing_result is None:
                raise ValueError(
                    "Duplicate unnumbered purchases must include the stored "
                    "result for the repeated request."
                )
            return outcome.existing_result

        raise ValueError(
            "Unsupported inventory outcome for unnumbered purchase: "
            f"{outcome.status}"
        )
