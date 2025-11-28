# Multi-stage build for ML Pipeline Orchestration

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY ml_pipeline/ ./ml_pipeline/
COPY tests/ ./tests/

# Create necessary directories
RUN mkdir -p /app/output /app/artifacts /app/logs

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; import os; requests.get(f'http://localhost:{os.getenv(\"API_PORT\", \"8000\")}/health')"

# Run the application
CMD ["python", "-m", "uvicorn", "ml_pipeline.api:app", "--host", "0.0.0.0", "--port", "8000"]