# Configuration Schema (Pydantic-based)

Layers: defaults → environment → tenant → persona → request

Example (YAML):
routing:
  default_provider: claude
  capabilities:
    tool_calling:
      providers: [claude, openai, bedrock-claude]
      fallback_order: [claude, openai]
  personas:
    backend_developer: { provider: openai }
    security_specialist: { provider: claude }
  tenants:
    tenant_a: { provider: azure, region: eastus }
    tenant_b: { provider: claude, budget_limit_usd: 100.0 }
experiments:
  new_provider_test:
    enabled: true
    traffic_percent: 10
    providers: [vertex, claude]
providers:
  claude:
    endpoint: https://api.anthropic.com
    model: claude-sonnet-4
    api_key_env: ANTHROPIC_API_KEY
    rate_limits: { rpm: 50, tpm: 100000 }
    retry: { max_attempts: 3, backoff_multiplier: 2 }
    circuit_breaker: { failure_threshold: 5, timeout_seconds: 30 }

Validation: Pydantic models, versioned schema, strict types; limited hot-reload (weights, routes).
