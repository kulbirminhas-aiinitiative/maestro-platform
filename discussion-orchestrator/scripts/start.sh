#!/bin/bash
set -e

# Discussion Orchestrator Start Script
# This script starts the Discussion Orchestrator service in development mode

echo "========================================="
echo "Starting Discussion Orchestrator Service"
echo "========================================="

# Navigate to the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Load environment variables if .env exists
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found. Using default values."
    echo "Consider copying .env.example to .env and configuring it."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations if any (placeholder for future)
# echo "Running database migrations..."
# python -m alembic upgrade head

# Check Redis connection
echo "Checking Redis connection..."
REDIS_URL=${REDIS_URL:-redis://localhost:6379}
if command -v redis-cli &> /dev/null; then
    if redis-cli -u "$REDIS_URL" ping > /dev/null 2>&1; then
        echo "✓ Redis connection successful"
    else
        echo "⚠ Warning: Cannot connect to Redis at $REDIS_URL"
        echo "  Make sure Redis is running or start it with: docker-compose up redis -d"
    fi
else
    echo "⚠ redis-cli not installed, skipping Redis connection check"
fi

# Set default port
SERVICE_PORT=${SERVICE_PORT:-5000}

echo ""
echo "========================================="
echo "Starting uvicorn server..."
echo "Service will be available at: http://localhost:$SERVICE_PORT"
echo "Health check: http://localhost:$SERVICE_PORT/health"
echo "API docs: http://localhost:$SERVICE_PORT/docs"
echo "========================================="
echo ""

# Start the server with auto-reload for development
uvicorn src.main:app \
    --host 0.0.0.0 \
    --port "$SERVICE_PORT" \
    --reload \
    --log-level info
