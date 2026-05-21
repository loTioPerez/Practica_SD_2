#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

: "${DATABASE_URL:?Set DATABASE_URL before running this script.}"

python3 -m elastic_ticketing.adapters.postgresql.schema create | psql "$DATABASE_URL"
