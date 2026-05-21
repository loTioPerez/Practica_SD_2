`src/elastic_ticketing/` is the application package.

Current implementation status:

- `core/`: business rules and purchase contracts. This is the most complete part.
- `adapters/postgresql/`: real persistence adapter for inventory, idempotency and completions.
- `adapters/rabbitmq/`, `apps/` and `verification/`: still pending implementation.

The project keeps the domain isolated from infrastructure so the same
`PurchaseService` can later be used from workers, benchmarks and tests.
