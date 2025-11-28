# Maestro Template Service - Production Dockerfile
# Strategic Template Engine for Maestro Platform

FROM python:3.11-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.0

WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./

# Install dependencies and configure Nexus
ARG PYPI_INDEX_URL=http://localhost:28081/repository/pypi-hosted/simple
ARG PYPI_TRUSTED_HOST=localhost

RUN pip config set global.index-url ${PYPI_INDEX_URL} && \
    pip config set global.trusted-host ${PYPI_TRUSTED_HOST}

# Configure Poetry to use Nexus
ARG NEXUS_PASSWORD=DJ6J&hGH!B#u*J
RUN poetry config virtualenvs.create false && \
    poetry config repositories.nexus ${PYPI_INDEX_URL} && \
    poetry config http-basic.nexus admin ${NEXUS_PASSWORD}

# Install dependencies
RUN poetry install --no-root --no-dev --no-interaction --no-ansi

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry in production stage
RUN pip install --no-cache-dir poetry==1.7.0

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy pyproject.toml and README.md for poetry run
COPY pyproject.toml README.md ./

# Copy application source
COPY src/ ./src/
COPY templates_storage/ ./templates_storage/
COPY config/ ./config/

# Create necessary directories
RUN mkdir -p logs && \
    mkdir -p templates_storage && \
    chmod -R 755 templates_storage

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose service port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# Run the application
CMD ["poetry", "run", "uvicorn", "template_service.app:app", "--host", "0.0.0.0", "--port", "8005"]
