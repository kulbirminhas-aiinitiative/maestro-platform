# Maestro Platform: Copilot Instructions

## Big Picture Architecture
- **Microservices**: The platform is composed of several Python microservices, each with a clear responsibility:
  - `multi-agent-service`: Orchestrates teams of AI agents with various engagement modes (sequential, parallel, debate, consensus). Integrates with LLM Router and RAG Service.
  - `llm-router`: Routes LLM requests to providers (Claude, OpenAI, Gemini) based on persona and capability policies. Configured via YAML files in `config/`.
  - `rag-service`: Handles document ingestion and semantic search using ChromaDB and sentence-transformers. Provides REST endpoints for ingest/search.
  - `llm-service`: Standalone LLM API with CI/CD pipeline, Redis integration, and health checks.

## Service Boundaries & Data Flow
- **Communication**: Services interact via REST APIs. Example: `multi-agent-service` calls `llm-router` and `rag-service` for agent orchestration and knowledge queries.
- **Persona Routing**: LLM requests are routed using persona/capability YAMLs (`llm-router/config/`).
- **Session Management**: `multi-agent-service` tracks chat sessions and team context.

## Developer Workflows
- **Local Development**:
  - Install dependencies: `poetry install`
  - Run services:
    - `multi-agent-service`: `poetry run python -m multi_agent.main`
    - `llm-router`: `poetry run python -m llm_router.main`
    - `rag-service`: `poetry run python -m uvicorn rag_service.main:app --host 0.0.0.0 --port 8002`
    - `llm-service`: `poetry run uvicorn src.llm-service.main:app --reload --port 8001`
  - Run tests (llm-service): `poetry run pytest`
  - Format code (llm-service): `poetry run black src/ tests/ --line-length 150` and `poetry run isort src/ tests/`
- **Docker**:
  - Build: `docker build -t <service>:latest .`
  - Run: See each service's README for port/env details
- **Configuration**:
  - Use environment variables or `.env` files. See `.env.example` in each service for options.

## Project-Specific Conventions
- **Persona/Provider Mapping**: Defined in YAML (`llm-router/config/persona_policy.yaml`, `capabilities.yaml`).
- **Engagement Modes**: `multi-agent-service` supports multiple agent interaction patterns (sequential, parallel, debate, consensus).
- **Session/Team APIs**: Consistent REST endpoints for managing teams and chat sessions.
- **Semantic Search**: RAG service uses ChromaDB and sentence-transformers for document similarity.

## Integration Points
- **LLM Providers**: Adapters for Claude, OpenAI, Gemini in `llm-router/src/llm_router/providers/`
- **Vector DB**: ChromaDB for semantic search in RAG service
- **Redis**: Used by llm-service for state management
- **CI/CD**: llm-service deploys via GitHub Actions on push to main/develop

## Key Files & Directories
- `multi-agent-service/README.md`: Orchestration, API, usage examples
- `llm-router/README.md`, `config/`: Routing logic, persona/capability YAMLs
- `rag-service/README.md`, `src/rag_service/`: Semantic search, ingestion logic
- `llm-service/README.md`: API, CI/CD, formatting/testing commands

## Example: Create a Team (multi-agent-service)
```bash
curl -X POST http://localhost:8003/api/v2/teams \
  -H "Content-Type: application/json" \
  -d '{"name": "Architecture Team", "members": [{"persona": "architect", "provider": "claude_agent"}]}'
```

## Example: Persona Routing (llm-router)
- Edit `config/persona_policy.yaml` to add new personas/providers

---
For unclear or missing conventions, review each service's README and config files. Ask maintainers for undocumented workflows.
