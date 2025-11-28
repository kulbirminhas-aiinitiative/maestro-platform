# Execution Platform Gateway Integration Plan

Scope: Migrate maestro-hive orchestrators/personas from claude_code_sdk/CLI to provider-agnostic Gateway (execution-platform).

Target interface: HTTP SSE + JSON over /v1/chat, /v1/tools/invoke, /v1/embeddings (see execution-platform/README.md).

Persona-scoped configuration
- Add persona_config.json and PersonaGatewayClient; orchestrators pass persona_id to select provider/tools per agent.
- No global service-level switch; routing decided per persona per request.

Touchpoints to refactor (phase-by-phase)
- Replace: claude_code_sdk.py usage with a thin Gateway client wrapper
- Update: persona_executor_v2.py, team_execution*_*.py, sdlc_* to emit messages/tools via Gateway
- Keep: tool_access_mapping.py semantics by mapping tools to ToolBridge names (fs_read, fs_write, etc.)

Minimal client wrapper contract (Python)
- stream_chat(messages, provider=None, tools=None, tool_choice=None, response_format=None) -> iterator of events {event, data}
- invoke_tool(name, args) -> result
- embeddings(input: list[str]) -> list[list[float]]

Rollout steps
1) Stand up execution-platform (Poetry or Docker). Ensure /v1/health/providers OK.
2) Implement gateway_client.py (wrapper) in maestro-hive using httpx or requests.
3) Switch one simple orchestrator to use gateway_client (feature-flagged).
Feature flag
- Set HIVE_USE_GATEWAY=1 to route a persona via Gateway. Optional GATEWAY_URL to override base.

4) Validate with existing demos; monitor SSE, tool events, usage, cost.
5) Gradually migrate remaining orchestrators; remove CLI dependency last.

Config
- Env: GATEWAY_URL (default http://localhost:8080)
- Provider override per run via query param provider=openai|anthropic|gemini|auto

Testing
- Use execution-platform tests as reference; add maestro-hive E2E smoke pointing at Gateway.

Backout
- Feature flag to revert to existing Claude CLI path.
