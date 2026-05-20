Core-focused tests can be run locally with:

```powershell
$env:PYTHONPATH = "src"
py -m unittest tests.test_correctness_requirements tests.test_fault_tolerance_requirements
```

These tests avoid RabbitMQ, AWS and PostgreSQL on purpose. They only verify
the current domain, validation, correctness and idempotency contracts.
