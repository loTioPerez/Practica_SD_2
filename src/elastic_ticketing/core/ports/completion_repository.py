from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.models import CompletionRecord


class CompletionRepository(ABC):
    """Persistence contract for completed request records used in analysis."""

    @abstractmethod
    def save_completion(self, record: CompletionRecord) -> None:
        """Persist one completed request record."""
