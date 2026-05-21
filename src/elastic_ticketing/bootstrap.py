from __future__ import annotations

from dataclasses import dataclass

from .adapters.postgresql import (
    PostgresCompletionRepository,
    PostgresTicketRepository,
    make_connection_factory,
)
from .core import (
    IdempotencyService,
    NumberedService,
    PurchaseService,
    UnnumberedService,
    ValidationService,
)
from .shared.config import PostgresSettings


@dataclass(frozen=True)
class PostgresAppContext:
    settings: PostgresSettings
    ticket_repository: PostgresTicketRepository
    completion_repository: PostgresCompletionRepository
    purchase_service: PurchaseService


def build_postgres_context(
    settings: PostgresSettings | None = None,
) -> PostgresAppContext:
    postgres_settings = settings or PostgresSettings.from_env()
    connection_factory = make_connection_factory(postgres_settings)

    ticket_repository = PostgresTicketRepository(connection_factory)
    completion_repository = PostgresCompletionRepository(connection_factory)
    validation_service = ValidationService()
    idempotency_service = IdempotencyService(ticket_repository)
    numbered_service = NumberedService(ticket_repository)
    unnumbered_service = UnnumberedService(ticket_repository)
    purchase_service = PurchaseService(
        validation_service=validation_service,
        idempotency_service=idempotency_service,
        numbered_service=numbered_service,
        unnumbered_service=unnumbered_service,
    )

    return PostgresAppContext(
        settings=postgres_settings,
        ticket_repository=ticket_repository,
        completion_repository=completion_repository,
        purchase_service=purchase_service,
    )


def build_postgres_purchase_service(
    settings: PostgresSettings | None = None,
) -> PurchaseService:
    return build_postgres_context(settings).purchase_service
