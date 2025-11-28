Config Schema (Pydantic outline)

routing:
  default_provider: str
  personas: dict[str, {provider: str, fallback: list[str]}]
  capabilities: dict[str, {providers: list[str], fallback_order: list[str]}]
  experiments?: dict[str, {enabled: bool, traffic_percent: int, providers: list[str]}]
providers:
  <name>:
    endpoint?: str
    model?: str
    api_key_env?: str
    rate_limits?: {rpm?: int, tpm?: int}
    retry?: {max_attempts: int, backoff_multiplier: float}
    circuit_breaker?: {failure_threshold: int, timeout_seconds: int}
