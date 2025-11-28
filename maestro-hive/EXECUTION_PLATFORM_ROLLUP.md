# Execution Platform Roll-up

- Master index: maestro-hive/PROVIDER_AGNOSTIC_MASTER_INDEX.md
- Gateway integration plan: maestro-hive/GATEWAY_INTEGRATION_PLAN.md
- Persona config and client: persona_config.json, persona_gateway_client.py, PERSONA_CONFIG.md
- Execution Platform project: execution-platform/ (Gateway, adapters, ToolBridge, tests, Docker)

Dev quickstart
1) cd execution-platform && poetry install && poetry run uvicorn execution_platform.gateway.app:app --reload --port 8080
2) cd maestro-hive && ./scripts/run_persona_via_gateway.sh

Notes
- Per-persona routing via persona_config.json; HIVE_USE_GATEWAY=1 to enable.
- Provide EP_* keys to exercise live providers.
