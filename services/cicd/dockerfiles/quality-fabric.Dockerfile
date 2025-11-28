# Quality Fabric - Testing as a Service Platform
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV POETRY_VERSION=1.8.0
ENV POETRY_HOME=/opt/poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_VIRTUALENVS_CREATE=true
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set work directory
WORKDIR /app

# Install system dependencies and Poetry
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        wget \
        gnupg \
        unzip \
        chromium \
        chromium-driver \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && rm -rf /var/lib/apt/lists/*

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Install Python dependencies using Poetry
RUN poetry install --no-root --only main

# Install Playwright browsers (optional)
RUN poetry run playwright install chromium || echo "Playwright installation failed, continuing..."

# Copy application code
COPY . .

# Create directories for results and logs
RUN mkdir -p /app/results /app/logs /app/temp

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application with Poetry
CMD ["poetry", "run", "python", "run_server.py"]
