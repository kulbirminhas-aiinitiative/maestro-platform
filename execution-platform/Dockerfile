FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml /app/
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi
COPY execution_platform /app/execution_platform
EXPOSE 8080
CMD ["uvicorn","execution_platform.gateway.app:app","--host","0.0.0.0","--port","8080"]
