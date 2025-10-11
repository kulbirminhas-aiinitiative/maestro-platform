FROM python:3.11-slim

LABEL maintainer="Maestro ML Team"
LABEL description="Maestro ML Platform - Self-aware ML development platform"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

# Add poetry and virtualenv to PATH
ENV PATH="$POETRY_HOME/bin:/app/.venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy poetry files first for better caching
COPY pyproject.toml poetry.lock* ./

# Install dependencies (no dev dependencies in production)
RUN poetry install --no-dev --no-root

# Copy application code
COPY . .

# Install the project itself
RUN poetry install --no-dev

# Create non-root user
RUN useradd -m -u 1000 maestro && \
    chown -R maestro:maestro /app

USER maestro

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default command - use Python from venv directly
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "maestro_ml.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
