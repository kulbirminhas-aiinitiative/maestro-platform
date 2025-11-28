#!/usr/bin/env bash
set -euo pipefail
export EP_PROVIDER=${EP_PROVIDER:-mock}
uvicorn execution_platform.gateway.app:app --host 0.0.0.0 --port 8080
