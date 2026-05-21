`src/elastic_ticketing/` is the application package.

Current implementation status:

- `core/`: business rules and purchase contracts. This is the most complete part.
- `adapters/postgresql/`: real persistence adapter for inventory, idempotency and completions.
- `adapters/rabbitmq/`: simple queue adapter with JSON messages, publisher, polling consumer and DLQ-ready queue declaration.
- `bootstrap.py`: simple wiring to build a `PurchaseService` backed by PostgreSQL.
- `apps/postgres_cli.py`: tiny local CLI to create/reset schema and try purchases by hand.
- `apps/worker/`: worker loop and Lambda-style entrypoint already wired to RabbitMQ + PostgreSQL.
- `apps/producer/`, `apps/scaler/`, `apps/analysis/` and `verification/`: still pending implementation.

The project keeps the domain isolated from infrastructure so the same
`PurchaseService` can later be used from workers, benchmarks and tests.
