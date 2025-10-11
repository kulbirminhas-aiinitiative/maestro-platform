#!/bin/bash
# Maestro ML Platform API Startup Script

echo "🚀 Starting Maestro ML Platform API..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "📍 Python version: $python_version"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies if needed
if [ ! -f ".venv/installed" ]; then
    echo "📦 Installing dependencies..."
    pip install -r api/requirements.txt
    touch .venv/installed
    echo "✅ Dependencies installed"
fi

# Check MLflow connection
echo "🔍 Checking MLflow connection..."
mlflow_uri=${MLFLOW_TRACKING_URI:-http://localhost:5000}
if curl -sf $mlflow_uri/health > /dev/null 2>&1; then
    echo "✅ MLflow is accessible at $mlflow_uri"
else
    echo "⚠️  MLflow not accessible at $mlflow_uri"
    echo "   Start MLflow with: mlflow server --host 0.0.0.0 --port 5000"
fi

# Check PDF service
echo "🔍 Checking PDF Generator Service..."
pdf_url=${PDF_SERVICE_URL:-http://localhost:9550}
if curl -sf $pdf_url/health > /dev/null 2>&1; then
    echo "✅ PDF Generator Service is accessible at $pdf_url"
else
    echo "⚠️  PDF Generator Service not accessible at $pdf_url"
    echo "   Start it with: cd ~/projects/utilities/services/pdf_generator && python app.py"
fi

# Set default environment variables
export MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI:-http://localhost:5000}
export PDF_SERVICE_URL=${PDF_SERVICE_URL:-http://localhost:9550}
export API_HOST=${API_HOST:-0.0.0.0}
export API_PORT=${API_PORT:-8000}

echo ""
echo "🌟 Starting API server..."
echo "📚 API Docs: http://localhost:${API_PORT}/docs"
echo "❤️  Health: http://localhost:${API_PORT}/health"
echo ""

# Start the server
uvicorn api.main:app \
    --host ${API_HOST} \
    --port ${API_PORT} \
    --reload \
    --log-level info
