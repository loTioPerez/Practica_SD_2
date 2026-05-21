Core-focused tests can be run locally with:

```powershell
$env:PYTHONPATH = "src"
py -m unittest `
  tests.test_correctness_requirements `
  tests.test_fault_tolerance_requirements `
  tests.test_postgresql_repositories `
  tests.test_worker_flow
```

These tests avoid RabbitMQ, AWS and PostgreSQL on purpose. They only verify
the current domain, validation, correctness and idempotency contracts.

Optional integration test:

```powershell
$env:PYTHONPATH = "src"
$env:ELASTIC_TICKETING_POSTGRES_TEST_DSN = "host=... port=5432 dbname=... user=... password=..."
py -m unittest tests.test_postgresql_integration
```

Use a disposable database for that test, because it resets the practice tables.
