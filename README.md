
### ESTRUCTURA PLANTEADA ###

Practica_SD2/
│
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
│
├── config/
│   ├── README.md
│   ├── common.yaml
│   ├── aws.yaml
│   ├── rabbitmq.yaml
│   ├── dynamodb.yaml
│   ├── lambda.yaml
│   ├── scaler.yaml
│   └── workload.yaml
│
├── infra/
│   ├── README.md
│   └── cloudformation/
│       ├── template.yaml
│       └── parameters.example.json
│
├── deploy/
│   ├── README.md
│   ├── rabbitmq/
│   │   ├── setup_rabbitmq_vm.sh
│   │   └── definitions.json
│   ├── lambda/
│   │   ├── build_lambda_zip.sh
│   │   ├── deploy_lambda.sh
│   │   └── invoke_worker.sh
│   └── dynamodb/
│       ├── create_tables.sh
│       ├── reset_tables.sh
│       └── delete_tables.sh
│
├── scripts/
│   ├── README.md
│   ├── init_experiment.sh
│   ├── reset_experiment.sh
│   ├── run_uniform_workload.sh
│   ├── run_hotspot_workload.sh
│   ├── run_elastic_workload.sh
│   ├── run_stress_test.sh
│   ├── start_scaler.sh
│   ├── stop_scaler.sh
│   ├── send_quit_workers.sh
│   ├── verify_correctness.sh
│   ├── collect_results.sh
│   └── generate_plots.sh
│
├── benchmarks/
│   ├── README.md
│   ├── input/
│   │   ├── benchmark_unnumbered_100000.txt
│   │   ├── benchmark_numbered_uniform.txt
│   │   └── benchmark_numbered_hotspot.txt
│   └── generated/
│       ├── generate_unnumbered.py
│       ├── generate_numbered_uniform.py
│       ├── generate_hotspot.py
│       └── generate_elastic_workload.py
│
├── results/
│   ├── README.md
│   ├── raw/
│   │   └── .gitkeep
│   ├── summaries/
│   │   └── .gitkeep
│   └── plots/
│       └── .gitkeep
│
├── src/
│   └── elastic_ticketing/
│       │
│       ├── shared/
│       │   ├── config.py
│       │   ├── constants.py
│       │   ├── logger.py
│       │   ├── exceptions.py
│       │   ├── serialization.py
│       │   └── health.py
│       │
│       ├── core/
│       │   ├── domain/
│       │   │   ├── models.py
│       │   │   └── enums.py
│       │   ├── services/
│       │   │   ├── purchase_service.py
│       │   │   ├── unnumbered_service.py
│       │   │   ├── numbered_service.py
│       │   │   ├── validation_service.py
│       │   │   └── idempotency_service.py
│       │   └── ports/
│       │       ├── ticket_repository.py
│       │       ├── request_repository.py
│       │       └── completion_repository.py
│       │
│       ├── adapters/
│       │   ├── rabbitmq/
│       │   │   ├── connection.py
│       │   │   ├── queue_setup.py
│       │   │   ├── publisher.py
│       │   │   ├── consumer.py
│       │   │   └── serializer.py
│       │   ├── dynamodb/
│       │   │   ├── connection.py
│       │   │   ├── table_names.py
│       │   │   ├── repositories.py
│       │   │   └── transactions.py
│       │   └── aws/
│       │       ├── lambda_client.py
│       │       └── cloudwatch_client.py
│       │
│       ├── apps/
│       │   ├── producer/
│       │   │   ├── main.py
│       │   │   ├── workload.py
│       │   │   └── benchmark_parser.py
│       │   ├── worker/
│       │   │   ├── handler.py
│       │   │   └── worker_loop.py
│       │   ├── scaler/
│       │   │   ├── main.py
│       │   │   ├── formulas.py
│       │   │   ├── rabbitmq_metrics.py
│       │   │   ├── scaling_policy.py
│       │   │   └── lambda_invoker.py
│       │   └── analysis/
│       │       ├── aggregate_results.py
│       │       ├── metrics.py
│       │       └── plots.py
│       │
│       └── verification/
│           ├── verify_unnumbered.py
│           ├── verify_numbered.py
│           ├── verify_idempotency.py
│           └── verify_completion_log.py
│
└── tests/
    ├── README.md
    ├── test_correctness_requirements.py
    ├── test_scaling_formulas.py
    ├── test_workload_generation.py
    ├── test_fault_tolerance_requirements.py
    └── test_metrics_calculation.py