#!/bin/bash
# Start the Execution Platform Gateway

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Starting Execution Platform Gateway                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Change to project directory
cd "$(dirname "$0")/.."

# Load environment variables
if [ -f .env ]; then
    echo "✅ Loading environment variables from .env"
    export $(cat .env | xargs)
fi

echo ""
echo "Gateway Configuration:"
echo "  Host: 0.0.0.0"
echo "  Port: 8000"
echo "  Reload: enabled"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "API Endpoints:"
echo "  Health:       http://localhost:8000/health"
echo "  Capabilities: http://localhost:8000/capabilities"
echo "  Chat:         http://localhost:8000/chat"
echo "  Costs:        http://localhost:8000/costs"
echo "  Docs:         http://localhost:8000/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the gateway
poetry run uvicorn execution_platform.gateway.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info
