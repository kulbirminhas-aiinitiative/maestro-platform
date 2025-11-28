# Persona-scoped Provider Routing

- File: persona_config.json
- Schema per persona_id:
  { "provider": "openai|anthropic|gemini|mock|auto", "tools": ["fs_read",...], "fallback": ["openai", ...] }

Usage
- Use PersonaGatewayClient in maestro-hive agents to stream chat via the Execution Platform with persona-specific provider and tools.
- Env: GATEWAY_URL=http://host:8080

Example
{
Feature flag
- Export HIVE_USE_GATEWAY=1 to enable Gateway in persona_executor_v2.
- GATEWAY_URL=http://localhost:8080 to point at the execution-platform.

  "default": { "provider": "auto", "tools": [], "fallback": ["openai", "anthropic", "mock"] },
  "backend_developer": { "provider": "openai", "tools": ["fs_read", "fs_write", "echo"], "fallback": ["anthropic", "mock"] }
Fallback
- Each persona can specify fallback providers; PersonaGatewayClient will attempt them in order if streaming fails.

}
