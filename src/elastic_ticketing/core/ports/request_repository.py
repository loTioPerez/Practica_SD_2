from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.models import PurchaseResult


class RequestRepository(ABC):
    """
    Read access to processed requests.

    The idempotency service will use this port to detect whether a request_id
    has already been completed and can safely reuse the stored result.
    """

    @abstractmethod
    def get_existing_result(self, request_id: str) -> PurchaseResult | None:
        """Return the stored result for a completed request, if any."""
