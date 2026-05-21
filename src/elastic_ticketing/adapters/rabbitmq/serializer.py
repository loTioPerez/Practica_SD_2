from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ...core import PurchaseRequest, TicketType
from ...shared.exceptions import SerializationError
from ...shared.serialization import (
    datetime_to_iso,
    json_dumps_bytes,
    json_loads_bytes,
    parse_optional_datetime,
)

PURCHASE_MESSAGE_KIND = "purchase"
QUIT_MESSAGE_KIND = "quit"


@dataclass(frozen=True)
class QueueMessage:
    kind: str
    request_id: str | None = None
    client_id: str | None = None
    ticket_type: TicketType | None = None
    seat_id: int | None = None
    experiment_id: str | None = None
    queued_at: datetime | None = None
    attempt: int = 1

    @property
    def is_quit(self) -> bool:
        return self.kind == QUIT_MESSAGE_KIND

    @classmethod
    def from_purchase_request(
        cls,
        request: PurchaseRequest,
        *,
        queued_at: datetime | None = None,
        attempt: int = 1,
    ) -> "QueueMessage":
        return cls(
            kind=PURCHASE_MESSAGE_KIND,
            request_id=request.request_id,
            client_id=request.client_id,
            ticket_type=request.ticket_type,
            seat_id=request.seat_id,
            experiment_id=request.experiment_id,
            queued_at=queued_at,
            attempt=attempt,
        )

    @classmethod
    def quit(cls) -> "QueueMessage":
        return cls(kind=QUIT_MESSAGE_KIND)

    def to_purchase_request(self) -> PurchaseRequest:
        if self.is_quit:
            raise SerializationError("QUIT messages do not contain a purchase request.")
        if not self.request_id or not self.client_id or self.ticket_type is None:
            raise SerializationError("Purchase messages must include request fields.")
        return PurchaseRequest(
            request_id=self.request_id,
            client_id=self.client_id,
            ticket_type=self.ticket_type,
            seat_id=self.seat_id,
            experiment_id=self.experiment_id,
        )


def serialize_queue_message(message: QueueMessage) -> bytes:
    payload = {
        "kind": message.kind,
        "request_id": message.request_id,
        "client_id": message.client_id,
        "ticket_type": message.ticket_type.value if message.ticket_type else None,
        "seat_id": message.seat_id,
        "experiment_id": message.experiment_id,
        "queued_at": datetime_to_iso(message.queued_at),
        "attempt": message.attempt,
    }
    return json_dumps_bytes(payload)


def deserialize_queue_message(data: bytes | str) -> QueueMessage:
    payload = json_loads_bytes(data)
    kind = payload.get("kind")
    if kind == QUIT_MESSAGE_KIND:
        return QueueMessage.quit()
    if kind != PURCHASE_MESSAGE_KIND:
        raise SerializationError(f"Unsupported queue message kind: {kind!r}")

    ticket_type_value = payload.get("ticket_type")
    try:
        ticket_type = TicketType(ticket_type_value)
    except ValueError as exc:
        raise SerializationError(
            f"Unsupported ticket type in queue message: {ticket_type_value!r}"
        ) from exc

    attempt = payload.get("attempt", 1)
    if not isinstance(attempt, int) or attempt < 1:
        raise SerializationError("Queue message attempt must be an integer >= 1.")

    return QueueMessage(
        kind=PURCHASE_MESSAGE_KIND,
        request_id=payload.get("request_id"),
        client_id=payload.get("client_id"),
        ticket_type=ticket_type,
        seat_id=payload.get("seat_id"),
        experiment_id=payload.get("experiment_id"),
        queued_at=parse_optional_datetime(payload.get("queued_at")),
        attempt=attempt,
    )
