FROM python:3.11-slim

LABEL maintainer="Maestro Platform Team"
LABEL service="automation-service"
LABEL version="1.0.0"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.0

# Copy dependency files
COPY pyproject.toml ./

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install dependencies
ARG PYPI_INDEX_URL=http://maestro-nexus:8081/repository/pypi-group/simple
ARG PYPI_TRUSTED_HOST=maestro-nexus

RUN pip config set global.index-url ${PYPI_INDEX_URL} && \
    pip config set global.trusted-host ${PYPI_TRUSTED_HOST}

# Install Python dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Copy application source
COPY src/ ./src/

# Create logs directory
RUN mkdir -p /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Expose port
EXPOSE 8003

# Run service
CMD ["uvicorn", "automation_service.main:app", "--host", "0.0.0.0", "--port", "8003", "--log-level", "info"]
