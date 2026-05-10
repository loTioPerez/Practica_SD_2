from __future__ import annotations

from enum import Enum


class TicketType(str, Enum):
    UNNUMBERED = "unnumbered"
    NUMBERED = "numbered"


class PurchaseStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RejectionReason(str, Enum):
    SOLD_OUT = "sold_out"
    SEAT_ALREADY_SOLD = "seat_already_sold"
    DUPLICATE_REQUEST = "duplicate_request"
    INVALID_CLIENT_ID = "invalid_client_id"
    INVALID_REQUEST_ID = "invalid_request_id"
    INVALID_SEAT_ID = "invalid_seat_id"
    MISSING_SEAT_ID = "missing_seat_id"
    UNEXPECTED_SEAT_ID = "unexpected_seat_id"
    INVALID_TICKET_TYPE = "invalid_ticket_type"


class SeatStatus(str, Enum):
    AVAILABLE = "available"
    SOLD = "sold"


class InventoryPurchaseStatus(str, Enum):
    PURCHASED = "purchased"
    SOLD_OUT = "sold_out"
    SEAT_ALREADY_SOLD = "seat_already_sold"
    DUPLICATE_REQUEST = "duplicate_request"
