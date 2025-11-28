#!/usr/bin/env bash
set -euo pipefail
export HIVE_USE_GATEWAY=1
export GATEWAY_URL=${GATEWAY_URL:-http://localhost:8080}
python3 persona_executor_v2.py --persona-id backend_developer --requirement "Create a README" --output ./generated_gateway
