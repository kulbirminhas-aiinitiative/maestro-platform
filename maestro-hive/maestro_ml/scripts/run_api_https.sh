#!/bin/bash
#
# Run Maestro ML API with HTTPS/TLS Support
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_ROOT/certs"

# Configuration
HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8443}"
HTTP_PORT="${HTTP_PORT:-8000}"
WORKERS="${API_WORKERS:-4}"
MODE="${1:-https}"  # https or http

echo "🚀 Starting Maestro ML API"
echo "============================"
echo ""

# Check if running in HTTPS mode
if [ "$MODE" = "https" ]; then
    # Check if certificates exist
    if [ ! -f "$CERTS_DIR/key.pem" ] || [ ! -f "$CERTS_DIR/cert.pem" ]; then
        echo "⚠️  TLS certificates not found!"
        echo "   Generating self-signed certificates..."
        echo ""
        "$PROJECT_ROOT/scripts/generate_self_signed_certs.sh"
        echo ""
    fi
    
    echo "🔒 Mode: HTTPS (TLS Enabled)"
    echo "📍 Address: https://$HOST:$PORT"
    echo "🔑 Certificate: $CERTS_DIR/cert.pem"
    echo "🔐 Private Key: $CERTS_DIR/key.pem"
    echo "👷 Workers: $WORKERS"
    echo ""
    
    # Start with HTTPS
    cd "$PROJECT_ROOT"
    poetry run uvicorn api.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --ssl-keyfile "$CERTS_DIR/key.pem" \
        --ssl-certfile "$CERTS_DIR/cert.pem" \
        --log-level info
else
    echo "🔓 Mode: HTTP (No TLS)"
    echo "📍 Address: http://$HOST:$HTTP_PORT"
    echo "👷 Workers: $WORKERS"
    echo ""
    echo "⚠️  WARNING: Running without TLS encryption!"
    echo "   For production, use HTTPS mode: $0 https"
    echo ""
    
    # Start with HTTP
    cd "$PROJECT_ROOT"
    poetry run uvicorn api.main:app \
        --host "$HOST" \
        --port "$HTTP_PORT" \
        --workers "$WORKERS" \
        --log-level info
fi
