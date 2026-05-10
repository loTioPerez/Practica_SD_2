from __future__ import annotations

from ..domain.models import PurchaseResult
from ..ports import RequestRepository


class IdempotencyService:
    def __init__(self, request_repository: RequestRepository) -> None:
        self._request_repository = request_repository

    def get_existing_result(self, request_id: str) -> PurchaseResult | None:
        return self._request_repository.get_existing_result(request_id)

    def is_duplicate(self, request_id: str) -> bool:
        return self.get_existing_result(request_id) is not None
