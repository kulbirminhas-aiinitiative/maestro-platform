# Migration Checklist: Maestro Hive -> Execution Platform Gateway (Persona-scoped)

Prereq
- execution-platform up (Poetry or Docker); health OK; EP_PROVIDER=mock for dev
- HIVE_USE_GATEWAY=1 set in environment

Steps
1) Configure persona_config.json per agent (provider, tools, fallback)
2) Use PersonaGatewayClient in agent code paths (start with low-risk persona)
3) Run E2E tests: pytest -q tests/test_gateway_persona_e2e.py tests/test_gateway_multiple_personas_e2e.py
4) Enable JSON mode where needed; validate with tests/test_gateway_persona_json_mode.py
5) Provide EP_* keys; run execution-platform/tests/test_live_providers.py (skips without keys)
6) Gradual rollout via feature flag; monitor logs and SSE events
7) Remove CLI-specific code after all personas migrated and stable

Backout
- Unset HIVE_USE_GATEWAY to revert to existing Claude CLI path
