# Maestro Provider-Agnostic SDK and Gateway Plan

## 1) Executive summary
Goal: decouple Maestro from any single LLM/tooling vendor by introducing a stable Service Provider Interface (SPI) and a single Gateway API consumed by frontend and backend. Adapters map SPI to providers (Claude, OpenAI/Azure, Vertex/PaLM, Bedrock, Local), with capability detection, routing, fallback, and observability. Migration wraps claude_code_sdk.py first, then refactors orchestrators to the SPI.

Outcomes:
- One API and SDK surface for apps and services (REST/WebSocket/GraphQL optional).
- Plug-and-play providers without changing orchestration/personas code.
- Config-based routing, AB testing, cost caps, and automatic failover.
- Contract tests ensure parity across providers.

---

## 2) Architecture overview

Layers:
1. Gateway API (northbound): single interface for UI/services.
2. Core SPI (Maestro SDK): provider-agnostic contracts used by orchestrators/personas.
3. Provider Adapters: Claude, OpenAI/Azure, Vertex/PaLM, Bedrock, Local (Ollama/vLLM).
4. Platform Services: ToolBridge (MCP/tools), MemoryStore (KV+Vector), EventBus, Tracing.
5. Policy & Routing: ProviderRouter, quotas, tenancy, circuit breakers.

Data flow:
Frontend/Backend → Gateway → Core SPI → Adapter → Provider
                                    ↘ ToolBridge → External tools
                                    ↘ Memory/EventBus/Tracing

---

## 3) Gateway API (single interface)
- Protocols: REST + WebSocket (streaming). GraphQL optional later with subscriptions.
- Core endpoints:
  - POST /v1/chat: chat completion (sync or streaming).
  - POST /v1/tools/invoke: tool calls via ToolBridge.
  - POST /v1/embeddings: embed text/batches.
  - POST /v1/jobs: long-running batch; GET /v1/jobs/{id} status; WS for updates.
  - GET /v1/events/stream: server events (WS) for tool/agent lifecycle.
- Auth: bearer + per-tenant keys; quotas/limits at gateway; per-provider policies.
- Schemas: provider-neutral request/response, JSON-schema for tool definitions, consistent token/logprobs/usage fields with graceful degradation.

---

## 4) Core SPI (Service Provider Interface)
Interfaces (Python typing shown; language-agnostic design):

- LLMClient
  - chat(req: ChatRequest) -> ChatResponse | stream(ChatChunk)
  - supports: capability flags (json_schema_tools, system_prompt, tool_choice, vision, long_context, reasoning, streaming)
- ToolBridge
  - register(tool: ToolSpec) -> id; invoke(id, args, ctx) -> ToolResult; mcp compatibility
- EmbeddingsClient
  - embed(inputs: list[str], model_hint?) -> EmbeddingResult(s)
- Files/BatchClient (optional, pluggable)
  - upload/download; submit batch; track status
- Tracer
  - trace(span, events, metrics); provider metadata & cost usage

Contracts: ChatRequest includes messages, tools (JSON schema), tool_choice, system, temperature, max_tokens, stop, response_format; ChatResponse includes text, tool_calls, usage, raw_provider_metadata.

---

## 5) Provider adapters
- ClaudeAdapter: wrap claude_code_sdk.py; map tool use and streaming; capture usage.
- OpenAIAdapter: chat.completions; function/tool_calls; JSON schema; streaming SSE.
- AzureOpenAIAdapter: same as OpenAI with deployment routing.
- VertexAdapter: Gemini chat, tools, safety settings; streaming.
- BedrockAdapter: model-agnostic; tool calling where supported; throttling backoff.
- LocalAdapter: Ollama/vLLM; best-effort tools via structured-output or ReAct shim.

Each adapter implements capability flags; polyfills (e.g., tool use via tool-call prompting when provider lacks native support). All adapters must pass contract tests.

---

## 6) Routing, policy, and resilience
- ProviderRouter strategies: round-robin, weighted, capability-matching, cost-aware, performance-aware, AB buckets.
- Fallback: automatic retry on transient failures; circuit breaker per provider/model.
- Limits: per-tenant budgets, rate limits, max concurrent streams/jobs.
- Deterministic replay: request hashing to maintain sticky routing when needed.

---

## 7) Platform services
- MemoryStore: KV (Redis-compatible) + Vector (FAISS/Qdrant/PGV); provider-neutral.
- EventBus: pub/sub for lifecycle (Kafka/NATS/Redis Streams); WS fan-out to clients.
- Tracing & Metrics: OpenTelemetry; spans for chat, tools, adapter calls; usage/costs.
- Schema registry: versioned tool schemas; validation; backward-compat diffs.

---

## 8) Migration plan
Phase 0 (scaffold):
- Introduce SPI types and Core SDK (no behavior changes).
- Add ClaudeAdapter wrapping claude_code_sdk.py.
- Create Gateway with /v1/chat passthrough to ClaudeAdapter.

Phase 1 (refactor orchestrators):
- Update persona_executor_v2.py, team_execution*.py, sdlc_* to consume SPI LLMClient and ToolBridge only.
- Keep tool_access_mapping.py unchanged; wire into ToolBridge.

Phase 2 (multi-provider):
- Add OpenAIAdapter + EmbeddingsClient implementations.
- Enable config-based provider selection per-skill/persona.
- Add ProviderRouter, circuit breaker, and basic quotas.

Phase 3 (enterprise hardening):
- Add Azure/Vertex/Bedrock/Local adapters.
- Observability (OTel), cost tracking, tenancy, event streaming.

Phase 4 (optimization):
- Advanced routing (SLA, cost/perf), batch APIs, offline mode, caching.

Rollback: env flag GATEWAY_PROVIDER=claude-only to revert quickly.

---

## 9) Configuration
- Single config file (yaml/env):
  - default_provider, model mappings per capability, per-skill overrides
  - weights, AB buckets, retry/backoff, budgets, rate limits
  - endpoints/keys per provider; feature flags
- Hot-reload support for low-risk changes.

---

## 10) Testing strategy
- Contract tests: same prompts/tools across adapters; golden responses within tolerances; tool-call conformance via JSON schema.
- E2E tests: run example_scenarios.py, team_execution_v2_split_mode.py via Gateway.
- Chaos tests: provider failure injection; retry/fallback correctness.
- Performance: p50/p95 latency SLAs; cost per output token; streaming smoothness.

---

## 11) Security and compliance
- Secrets via env/secret manager; no keys in code.
- Tenant isolation in Memory/EventBus; per-tenant quotas.
- Audit logs: who called what model/tool; retention.

---

## 12) Roadmap (high level with acceptance criteria)
- P0 (1 week):
  - SPI skeleton + ClaudeAdapter; Gateway /v1/chat streaming; basic contract tests.
  - AC: End-to-end chat via Gateway matches current Claude behavior.
- P1 (2 weeks):
  - OpenAIAdapter + EmbeddingsClient; ProviderRouter v1; config-driven selection.
  - AC: Switch providers without code changes; embeddings parity validated.
- P2 (2 weeks):
  - Azure/Vertex adapters; tracing + basic quotas; ToolBridge MCP parity.
  - AC: Tool calls work across providers; traces visible; quota enforcement.
- P3 (2 weeks):
  - Bedrock/LocalAdapter; offline/dev mode; chaos/fallback.
  - AC: Local runs succeed; failure drills pass.
- P4 (ongoing):
  - Advanced routing/cost optimization; batch jobs; caching.

---

## 13) Execution plan (detailed WBS)
Week 1 (P0):
- Add module maestro_sdk/ with interfaces (llm_client.py, tool_bridge.py, embeddings.py, tracing.py, types.py).
- Implement ClaudeAdapter; wire minimal Gateway (FastAPI/Flask) at gateway/app.py.
- Contract test harness tests/contract/ across providers (start with Claude only).

Week 2-3 (P1):
- OpenAIAdapter; embeddings (OpenAI + local fallback); ProviderRouter v1; config loader.
- Refactor persona_executor_v2.py, team_execution_v2.py, sdlc_workflow.py to use SPI.

Week 4-5 (P2):
- Azure/Vertex adapters; ToolBridge MCP adapter; quotas + tracing (OTel exporter).
- E2E through Gateway for demos (demo_* scripts via HTTP/WS).

Week 6-7 (P3):
- Bedrock/Local adapters; offline mode; chaos testing & circuit breakers.

Week 8+ (P4):
- Batch jobs, caching, advanced routing; cost dashboards; AB testing infra.

RACI (suggested):
- Lead: Platform architect
- Adapters: Provider specialists
- Gateway: Backend engineer
- Refactors/tests: Orchestration engineer
- Observability/security: SRE

---

## 14) Integration points in this repo
- Wrap: claude_code_sdk.py
- Refactor callers: persona_executor_v2.py, team_execution*.py, sdlc_* engines, phase_* orchestrators
- Keep stable: tool_access_mapping.py, review_tools.py (migrate to ToolBridge gradually)
- Demos: route demo_* through Gateway for parity checks

---

## 15) Risks and mitigations
- Provider feature gaps: polyfills + capability flags + graceful degradation.
- Cost drift: cost-aware routing + budgets.
- Latency variance: adaptive routing + caching + streaming.
- Vendor outages: multi-provider fallback + circuit breakers.

---

## 16) Deliverables checklist
- SPI package + adapters (Claude, OpenAI; later Azure/Vertex/Bedrock/Local)
- Gateway service with REST/WS
- Config + secrets plumbing
- Contract/E2E/chaos tests
- Runbooks and rollout plan with env flags
