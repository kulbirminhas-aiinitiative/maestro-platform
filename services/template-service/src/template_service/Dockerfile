FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.7.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_VIRTUALENVS_CREATE=true
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry --version

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies (including dev for local testing)
RUN poetry install --no-root --no-interaction --no-ansi

# Copy application code
COPY . .

# Install the package itself
RUN poetry install --only-root --no-interaction --no-ansi

# Create necessary directories
RUN mkdir -p /app/logs /app/config

# Expose port
EXPOSE 9600

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9600/health || exit 1

# Run the application using Poetry
CMD ["poetry", "run", "python", "app.py"]