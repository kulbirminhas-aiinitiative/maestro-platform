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
COPY pyproject.toml ./

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY src/ ./src/
COPY templates_storage/ ./templates_storage/

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
CMD ["uvicorn", "template_service.app:app", "--host", "0.0.0.0", "--port", "8005"]
