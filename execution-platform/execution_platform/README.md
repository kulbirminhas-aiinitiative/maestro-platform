# Execution Platform (Gateway + SPI)

This package provides a provider-agnostic LLM Gateway and SPI adapters for OpenAI, Gemini, Anthropic, and a shim for Claude Agent SDK usage.

Quick start
- poetry install
- poetry run uvicorn execution_platform.gateway.app:app --port 8080 --reload

Docs are under execution_platform/docs and the master index in maestro-hive: PROVIDER_AGNOSTIC_MASTER_INDEX.md.
