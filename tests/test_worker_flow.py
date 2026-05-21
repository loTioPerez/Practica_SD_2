from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from elastic_ticketing.adapters.rabbitmq.serializer import (  # noqa: E402
    QueueMessage,
    serialize_queue_message,
)
from elastic_ticketing.apps.worker.worker_loop import WorkerLoop  # noqa: E402
from elastic_ticketing.core import (  # noqa: E402
    CompletionRecord,
    PurchaseRequest,
    PurchaseResult,
    PurchaseStatus,
    RejectionReason,
    TicketType,
)
from elastic_ticketing.shared.config import WorkerSettings  # noqa: E402


@dataclass(frozen=True)
class FakeDelivery:
    body: bytes


class FakeConsumer:
    def __init__(self, deliveries: list[FakeDelivery]) -> None:
        self._deliveries = list(deliveries)
        self.acked: list[FakeDelivery] = []
        self.rejected: list[tuple[FakeDelivery, bool]] = []

    def get_message(self) -> FakeDelivery | None:
        if not self._deliveries:
            return None
        return self._deliveries.pop(0)

    def ack(self, delivery: FakeDelivery) -> None:
        self.acked.append(delivery)

    def reject(self, delivery: FakeDelivery, *, requeue: bool = False) -> None:
        self.rejected.append((delivery, requeue))


class FakePublisher:
    def __init__(self) -> None:
        self.messages: list[QueueMessage] = []

    def publish_message(self, message: QueueMessage) -> None:
        self.messages.append(message)


class FakeCompletionRepository:
    def __init__(self) -> None:
        self.records: list[CompletionRecord] = []

    def save_completion(self, record: CompletionRecord) -> None:
        self.records.append(record)


class FakePurchaseService:
    def __init__(self, result: PurchaseResult | None = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.requests: list[PurchaseRequest] = []

    def buy(self, request: PurchaseRequest) -> PurchaseResult:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class WorkerLoopTests(unittest.TestCase):
    def test_completed_purchase_is_saved_before_ack(self) -> None:
        request = PurchaseRequest(
            request_id="req-1",
            client_id="client-1",
            ticket_type=TicketType.UNNUMBERED,
        )
        message = QueueMessage.from_purchase_request(
            request,
            queued_at=datetime(2026, 5, 21, 20, 0, 0),
        )
        consumer = FakeConsumer([FakeDelivery(serialize_queue_message(message))])
        completion_repository = FakeCompletionRepository()
        purchase_service = FakePurchaseService(
            result=PurchaseResult.accepted_for(request)
        )
        sleep_calls: list[float] = []

        loop = WorkerLoop(
            consumer=consumer,
            purchase_service=purchase_service,
            completion_repository=completion_repository,
            worker_id="worker-1",
            sleep_fn=sleep_calls.append,
        )

        summary = loop.run()

        self.assertEqual(summary.completed_purchases, 1)
        self.assertEqual(summary.stop_reason, "queue_empty")
        self.assertEqual(len(consumer.acked), 1)
        self.assertEqual(len(completion_repository.records), 1)
        self.assertEqual(sleep_calls, [0.1])
        record = completion_repository.records[0]
        self.assertEqual(record.request_id, "req-1")
        self.assertEqual(record.worker_id, "worker-1")
        self.assertEqual(record.queued_at, datetime(2026, 5, 21, 20, 0, 0))

    def test_quit_message_stops_worker_cleanly(self) -> None:
        consumer = FakeConsumer([FakeDelivery(serialize_queue_message(QueueMessage.quit()))])
        completion_repository = FakeCompletionRepository()
        purchase_service = FakePurchaseService(
            result=PurchaseResult.rejected_for(
                PurchaseRequest(
                    request_id="unused",
                    client_id="unused",
                    ticket_type=TicketType.UNNUMBERED,
                ),
                RejectionReason.SOLD_OUT,
            )
        )

        loop = WorkerLoop(
            consumer=consumer,
            purchase_service=purchase_service,
            completion_repository=completion_repository,
            worker_id="worker-2",
        )

        summary = loop.run()

        self.assertEqual(summary.stop_reason, "quit_message")
        self.assertEqual(summary.completed_purchases, 0)
        self.assertEqual(len(consumer.acked), 1)
        self.assertEqual(len(completion_repository.records), 0)

    def test_failures_are_republished_with_incremented_attempt(self) -> None:
        request = PurchaseRequest(
            request_id="req-2",
            client_id="client-2",
            ticket_type=TicketType.NUMBERED,
            seat_id=4,
        )
        message = QueueMessage.from_purchase_request(request, attempt=1)
        consumer = FakeConsumer([FakeDelivery(serialize_queue_message(message))])
        publisher = FakePublisher()

        loop = WorkerLoop(
            consumer=consumer,
            purchase_service=FakePurchaseService(error=RuntimeError("temporary error")),
            completion_repository=FakeCompletionRepository(),
            publisher=publisher,
            worker_id="worker-3",
            settings=WorkerSettings(max_messages_per_invocation=10, max_attempts=3),
        )

        summary = loop.run()

        self.assertEqual(summary.retried_messages, 1)
        self.assertEqual(len(consumer.acked), 1)
        self.assertEqual(len(consumer.rejected), 0)
        self.assertEqual(len(publisher.messages), 1)
        self.assertEqual(publisher.messages[0].attempt, 2)

    def test_failures_go_to_dlq_after_max_attempts(self) -> None:
        request = PurchaseRequest(
            request_id="req-3",
            client_id="client-3",
            ticket_type=TicketType.UNNUMBERED,
        )
        message = QueueMessage.from_purchase_request(request, attempt=3)
        consumer = FakeConsumer([FakeDelivery(serialize_queue_message(message))])
        publisher = FakePublisher()

        loop = WorkerLoop(
            consumer=consumer,
            purchase_service=FakePurchaseService(error=RuntimeError("permanent error")),
            completion_repository=FakeCompletionRepository(),
            publisher=publisher,
            worker_id="worker-4",
            settings=WorkerSettings(max_messages_per_invocation=10, max_attempts=3),
        )

        summary = loop.run()

        self.assertEqual(summary.rejected_messages, 1)
        self.assertEqual(len(consumer.acked), 0)
        self.assertEqual(len(consumer.rejected), 1)
        self.assertEqual(consumer.rejected[0][1], False)
        self.assertEqual(len(publisher.messages), 0)


if __name__ == "__main__":
    unittest.main()
