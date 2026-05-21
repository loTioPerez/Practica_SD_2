from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from time import sleep
from typing import Protocol

from ...adapters.rabbitmq import QueueMessage, deserialize_queue_message
from ...core import CompletionRecord, CompletionRepository, PurchaseService
from ...shared.config import WorkerSettings
from ...shared.constants import PAYMENT_DELAY_MS


class DeliveryLike(Protocol):
    body: bytes


class ConsumerLike(Protocol):
    def get_message(self) -> DeliveryLike | None: ...

    def ack(self, delivery: DeliveryLike) -> None: ...

    def reject(self, delivery: DeliveryLike, *, requeue: bool = False) -> None: ...


class PublisherLike(Protocol):
    def publish_message(self, message: QueueMessage) -> None: ...


@dataclass(frozen=True)
class WorkerRunSummary:
    handled_messages: int
    completed_purchases: int
    retried_messages: int
    rejected_messages: int
    stop_reason: str


@dataclass(frozen=True)
class WorkerStepResult:
    completed_purchase: bool = False
    retried_message: bool = False
    rejected_message: bool = False
    stop_worker: bool = False
    stop_reason: str | None = None


class WorkerLoop:
    def __init__(
        self,
        *,
        consumer: ConsumerLike,
        purchase_service: PurchaseService,
        completion_repository: CompletionRepository,
        worker_id: str,
        settings: WorkerSettings | None = None,
        publisher: PublisherLike | None = None,
        now_fn=lambda: datetime.now(UTC),
        sleep_fn=sleep,
    ) -> None:
        self._consumer = consumer
        self._purchase_service = purchase_service
        self._completion_repository = completion_repository
        self._worker_id = worker_id
        self._settings = settings or WorkerSettings()
        self._publisher = publisher
        self._now_fn = now_fn
        self._sleep_fn = sleep_fn

    def run(self, max_messages: int | None = None) -> WorkerRunSummary:
        handled_messages = 0
        completed_purchases = 0
        retried_messages = 0
        rejected_messages = 0
        limit = max_messages or self._settings.max_messages_per_invocation

        while handled_messages < limit:
            delivery = self._consumer.get_message()
            if delivery is None:
                return WorkerRunSummary(
                    handled_messages=handled_messages,
                    completed_purchases=completed_purchases,
                    retried_messages=retried_messages,
                    rejected_messages=rejected_messages,
                    stop_reason="queue_empty",
                )

            handled_messages += 1
            step = self._process_delivery(delivery)
            if step.completed_purchase:
                completed_purchases += 1
            if step.retried_message:
                retried_messages += 1
            if step.rejected_message:
                rejected_messages += 1
            if step.stop_worker:
                return WorkerRunSummary(
                    handled_messages=handled_messages,
                    completed_purchases=completed_purchases,
                    retried_messages=retried_messages,
                    rejected_messages=rejected_messages,
                    stop_reason=step.stop_reason or "worker_stopped",
                )

        return WorkerRunSummary(
            handled_messages=handled_messages,
            completed_purchases=completed_purchases,
            retried_messages=retried_messages,
            rejected_messages=rejected_messages,
            stop_reason="message_limit",
        )

    def _process_delivery(self, delivery: DeliveryLike) -> WorkerStepResult:
        message: QueueMessage | None = None
        try:
            message = deserialize_queue_message(delivery.body)
            if message.is_quit:
                self._consumer.ack(delivery)
                return WorkerStepResult(
                    stop_worker=True,
                    stop_reason="quit_message",
                )

            request = message.to_purchase_request()
            started_at = self._now_fn()
            self._sleep_fn(PAYMENT_DELAY_MS / 1000)
            result = self._purchase_service.buy(request)
            completed_at = self._now_fn()
            self._completion_repository.save_completion(
                CompletionRecord(
                    request_id=result.request_id,
                    client_id=result.client_id,
                    ticket_type=result.ticket_type,
                    status=result.status,
                    seat_id=result.seat_id,
                    reason=result.reason,
                    experiment_id=request.experiment_id,
                    queued_at=message.queued_at,
                    started_at=started_at,
                    completed_at=completed_at,
                    worker_id=self._worker_id,
                    attempt=message.attempt,
                )
            )
            self._consumer.ack(delivery)
            return WorkerStepResult(completed_purchase=True)
        except Exception:
            if message is not None and not message.is_quit:
                return self._handle_failed_purchase(delivery, message)

            self._consumer.reject(delivery, requeue=False)
            return WorkerStepResult(rejected_message=True)

    def _handle_failed_purchase(
        self,
        delivery: DeliveryLike,
        message: QueueMessage,
    ) -> WorkerStepResult:
        if (
            self._publisher is not None
            and message.attempt < self._settings.max_attempts
        ):
            self._publisher.publish_message(
                replace(message, attempt=message.attempt + 1)
            )
            self._consumer.ack(delivery)
            return WorkerStepResult(retried_message=True)

        self._consumer.reject(delivery, requeue=False)
        return WorkerStepResult(rejected_message=True)
