Configuration is currently driven by environment variables.

Relevant files:

- `postgresql.yaml`: example values for the PostgreSQL adapter.
- `common.yaml`, `rabbitmq.yaml`, `lambda.yaml`, `scaler.yaml`: reserved for
  later phases.
- `dynamodb.yaml`: legacy scaffold kept only to avoid rewriting the original
  tree; PostgreSQL is now the active persistence backend.
