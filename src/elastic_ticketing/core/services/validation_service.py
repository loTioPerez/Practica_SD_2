from __future__ import annotations

from ..domain.enums import RejectionReason, TicketType
from ..domain.models import PurchaseRequest
from ...shared.constants import TOTAL_TICKETS


class ValidationService:
    def __init__(self, total_tickets: int = TOTAL_TICKETS) -> None:
        self._total_tickets = total_tickets

    def validate(self, request: PurchaseRequest) -> RejectionReason | None:
        if not self.is_valid_client_id(request.client_id):
            return RejectionReason.INVALID_CLIENT_ID

        if not self.is_valid_request_id(request.request_id):
            return RejectionReason.INVALID_REQUEST_ID

        if request.ticket_type is TicketType.UNNUMBERED:
            if request.seat_id is not None:
                return RejectionReason.UNEXPECTED_SEAT_ID
            return None

        if request.ticket_type is TicketType.NUMBERED:
            if request.seat_id is None:
                return RejectionReason.MISSING_SEAT_ID

            if not self.is_valid_seat_id(request.seat_id):
                return RejectionReason.INVALID_SEAT_ID
            return None

        return RejectionReason.INVALID_TICKET_TYPE

    def is_valid_client_id(self, client_id: str) -> bool:
        return isinstance(client_id, str) and bool(client_id.strip())

    def is_valid_request_id(self, request_id: str) -> bool:
        return isinstance(request_id, str) and bool(request_id.strip())

    def is_valid_seat_id(self, seat_id: int) -> bool:
        return (
            isinstance(seat_id, int)
            and not isinstance(seat_id, bool)
            and 1 <= seat_id <= self._total_tickets
        )
