FROM python:3.11-slim

LABEL maintainer="Maestro Platform Team"
LABEL service="k8s-execution-service"
LABEL version="1.0.0"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.0

# Copy dependency files
COPY pyproject.toml README.md ./

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install dependencies and configure Nexus
ARG PYPI_INDEX_URL=http://localhost:28081/repository/pypi-hosted/simple
ARG PYPI_TRUSTED_HOST=localhost

RUN pip config set global.index-url ${PYPI_INDEX_URL} && \
    pip config set global.trusted-host ${PYPI_TRUSTED_HOST}

# Configure Poetry to use Nexus
ARG NEXUS_PASSWORD=DJ6J&hGH!B#u*J
RUN poetry config repositories.nexus ${PYPI_INDEX_URL} && \
    poetry config http-basic.nexus admin ${NEXUS_PASSWORD}

# Install Python dependencies
RUN poetry install --no-root --no-dev --no-interaction --no-ansi

# Copy application source
COPY src/ ./src/
COPY templates/ ./templates/

# Create logs directory
RUN mkdir -p /app/logs

# Set PYTHONPATH so modules can be imported
ENV PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Expose port
EXPOSE 8004

# Run service
CMD ["poetry", "run", "uvicorn", "k8s_execution.main:app", "--host", "0.0.0.0", "--port", "8004", "--log-level", "info"]
