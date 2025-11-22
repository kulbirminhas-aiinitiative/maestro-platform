# Minimal Python image for LLM Router
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files
COPY pyproject.toml ./

# Configure poetry to not create virtualenv
RUN poetry config virtualenvs.create false

# Install only production dependencies
RUN poetry install --no-root --no-dev --no-interaction --no-ansi

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY claude_code_sdk.py ./
COPY README.md ./

# Install the package
RUN poetry install --only-root --no-interaction --no-ansi

# Create non-root user
RUN useradd -m -u 1000 llmrouter && \
    chown -R llmrouter:llmrouter /app

USER llmrouter

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the service
CMD ["python", "-m", "uvicorn", "llm_router.main:app", "--host", "0.0.0.0", "--port", "8001"]
