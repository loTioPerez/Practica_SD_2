from __future__ import annotations

from ..domain.enums import TicketType
from ..domain.models import PurchaseRequest, PurchaseResult
from .idempotency_service import IdempotencyService
from .numbered_service import NumberedService
from .unnumbered_service import UnnumberedService
from .validation_service import ValidationService


class PurchaseService:
    def __init__(
        self,
        validation_service: ValidationService,
        idempotency_service: IdempotencyService,
        numbered_service: NumberedService,
        unnumbered_service: UnnumberedService,
    ) -> None:
        self._validation_service = validation_service
        self._idempotency_service = idempotency_service
        self._numbered_service = numbered_service
        self._unnumbered_service = unnumbered_service

    def buy(self, request: PurchaseRequest) -> PurchaseResult:
        validation_error = self._validation_service.validate(request)
        if validation_error is not None:
            return PurchaseResult.rejected_for(request, validation_error)

        existing_result = self._idempotency_service.get_existing_result(
            request.request_id
        )
        if existing_result is not None:
            return existing_result

        if request.ticket_type is TicketType.UNNUMBERED:
            return self._unnumbered_service.buy(request)

        return self._numbered_service.buy(request)

    def buy_unnumbered(
        self,
        request_id: str,
        client_id: str,
        experiment_id: str | None = None,
    ) -> PurchaseResult:
        request = PurchaseRequest(
            request_id=request_id,
            client_id=client_id,
            ticket_type=TicketType.UNNUMBERED,
            experiment_id=experiment_id,
        )
        return self.buy(request)

    def buy_numbered(
        self,
        request_id: str,
        client_id: str,
        seat_id: int,
        experiment_id: str | None = None,
    ) -> PurchaseResult:
        request = PurchaseRequest(
            request_id=request_id,
            client_id=client_id,
            ticket_type=TicketType.NUMBERED,
            seat_id=seat_id,
            experiment_id=experiment_id,
        )
        return self.buy(request)
