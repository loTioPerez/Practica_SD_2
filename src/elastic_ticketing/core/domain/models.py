from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .enums import (
    InventoryPurchaseStatus,
    PurchaseStatus,
    RejectionReason,
    SeatStatus,
    TicketType,
)


@dataclass(frozen=True)
class PurchaseRequest:
    request_id: str
    client_id: str
    ticket_type: TicketType
    seat_id: int | None = None
    experiment_id: str | None = None


@dataclass(frozen=True)
class PurchaseResult:
    request_id: str
    client_id: str
    ticket_type: TicketType
    status: PurchaseStatus
    seat_id: int | None = None
    reason: RejectionReason | None = None

    @classmethod
    def accepted_for(cls, request: PurchaseRequest) -> "PurchaseResult":
        return cls(
            request_id=request.request_id,
            client_id=request.client_id,
            ticket_type=request.ticket_type,
            status=PurchaseStatus.ACCEPTED,
            seat_id=request.seat_id,
        )

    @classmethod
    def rejected_for(
        cls,
        request: PurchaseRequest,
        reason: RejectionReason,
    ) -> "PurchaseResult":
        return cls(
            request_id=request.request_id,
            client_id=request.client_id,
            ticket_type=request.ticket_type,
            status=PurchaseStatus.REJECTED,
            seat_id=request.seat_id,
            reason=reason,
        )


@dataclass(frozen=True)
class SeatInfo:
    seat_id: int
    status: SeatStatus
    sold_to_client_id: str | None = None
    sold_by_request_id: str | None = None


@dataclass(frozen=True)
class CompletionRecord:
    request_id: str
    client_id: str
    ticket_type: TicketType
    status: PurchaseStatus
    seat_id: int | None = None
    reason: RejectionReason | None = None
    experiment_id: str | None = None
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    worker_id: str | None = None
    attempt: int = 1


@dataclass(frozen=True)
class ExperimentInfo:
    experiment_id: str
    workload_name: str
    ticket_type: TicketType
    description: str | None = None


@dataclass(frozen=True)
class InventoryPurchaseOutcome:
    status: InventoryPurchaseStatus
    seat_info: SeatInfo | None = None
    existing_result: PurchaseResult | None = None

    @property
    def is_duplicate(self) -> bool:
        return self.status is InventoryPurchaseStatus.DUPLICATE_REQUEST
