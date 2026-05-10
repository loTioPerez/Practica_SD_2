from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.models import InventoryPurchaseOutcome, PurchaseRequest, SeatInfo


class TicketRepository(ABC):
    """
    Atomic inventory operations for numbered and unnumbered ticket sales.

    Concrete adapters are responsible for enforcing consistency and
    request-level idempotency when these operations hit the real backend.
    """

    @abstractmethod
    def purchase_unnumbered(
        self,
        request: PurchaseRequest,
    ) -> InventoryPurchaseOutcome:
        """Try to sell one unnumbered ticket for the given request."""

    @abstractmethod
    def purchase_numbered(
        self,
        request: PurchaseRequest,
    ) -> InventoryPurchaseOutcome:
        """Try to sell the requested numbered seat exactly once."""

    @abstractmethod
    def get_seat(self, seat_id: int) -> SeatInfo | None:
        """Return current seat information when it exists."""
