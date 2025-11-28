# Request: Expand maestro-templates to include execution-platform dependencies

Purpose: Support provider-agnostic Gateway + SPI + Adapters implementation.

Requested packages (Python)
- fastapi, uvicorn[standard], pydantic, httpx, anyio
- anthropic, openai
- opentelemetry-api, opentelemetry-sdk, opentelemetry-instrumentation-fastapi
- pytest, pytest-asyncio, ruff

Rationale
- google-generativeai

- FastAPI/Uvicorn/Pydantic: single Gateway API, validated schemas, SSE support
- httpx/anyio: async clients and concurrency primitives
- anthropic/openai: first two adapters (direct SDKs, no CLI)
- OpenTelemetry: traces/metrics from day one
- pytest stack + ruff: baseline quality gates

If templates provide alternatives, we will align and adjust requirements accordingly.
