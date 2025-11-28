# Library Alignment with maestro-templates

Status: Pending confirmation of maestro-templates package list. This document enumerates current execution-platform deps and flags proposed additions for template inclusion.

Core runtime
- fastapi — Gateway HTTP/SSE. Proposed addition (if not present).
- uvicorn[standard] — ASGI server. Proposed addition.
- pydantic — Config/models validation. Proposed addition.
- anyio, httpx — Async runtime and HTTP client. Proposed addition.

Provider SDKs
- anthropic — Direct Anthropic SDK (replacing CLI wrapper). Proposed addition.
- google-generativeai — Gemini adapter. Proposed addition.

- openai — Second provider adapter. Proposed addition.

Observability
- opentelemetry-api, opentelemetry-sdk, opentelemetry-instrumentation-fastapi — Tracing/metrics. Proposed addition.

Dev/Test
- pytest, pytest-asyncio — Tests. Proposed addition.
- ruff — Linting. Proposed addition.

Notes
- Will drop/replace any lib to match maestro-templates once the canonical list is provided.
- If maestro-templates already includes equivalents, we will reuse them and remove duplicates.
