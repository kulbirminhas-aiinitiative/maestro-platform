# AGENT3 SDK Feedback Response: Revised Plan and Execution Document

## 1) Summary of feedback and decisions
- Replace claude_code_sdk.py CLI wrapper with direct Anthropic Python SDK before introducing new layers.
- Treat tool calling abstraction as a first-class project: define a formal spec and tiered support.
- Specify SPI contracts rigorously (types, errors, streaming semantics), plus a capability matrix.
- Normalize streaming via SSE in Gateway; add buffering, backpressure, and resume strategy.
- Build a real configuration system (validated models, layered overrides) and comprehensive testing.
- Add cost tracking and budgets from day one; revise timelines to 6–9 months with phased milestones.

## 2) Revised architecture decisions
- Gateway → SPI → Adapters remains, but Phase 0 swaps out Node CLI for native SDK.
- ToolBridge mediates stateful ops (FS, Bash, Web) separate from LLM function calling; no misuse of provider "functions" for imperative ops.
- Capability-driven routing with fail-fast when persona requirements exceed provider capabilities.

## 3) Phased roadmap with realistic estimates and acceptance criteria
Phase 0 (4 weeks): Foundation
- Deliverables: Direct Anthropic integration; complete SPI v1.0; minimal HTTP Gateway; ClaudeAdapter; L0 API contract tests.
- AC: One simple orchestrator runs via Gateway with streaming; parity to current Claude flow; no Node CLI.

Phase 0.5 (3 weeks): Validation
- Deliverables: Run key demos E2E; latency/cost/error reports; gap log; Go/No-Go review.
- AC: <5% failure rate under load test; documented gaps with fixes scheduled.

Phase 1 (6 weeks): Second provider + tools
- Deliverables: OpenAIAdapter; Tool Calling Spec implemented for Tier 1/2; ProviderRouter v1; config system; L1 capability tests.
- AC: Personas that require tools run on Claude/OpenAI; routing switchable via config only.

Phase 2 (8 weeks): Enterprise readiness
- Deliverables: Azure+Vertex adapters; observability (OTel traces, metrics, logs); quotas/circuit breakers; cost tracking service; runbooks.
- AC: Error budgets/SLOs met in staging; cost dashboards live; tenant quotas enforced.

Phase 3 (6 weeks): Advanced providers and routing
- Deliverables: Bedrock adapter; Local adapter (best-effort Tier 3); AB testing; caching; batch APIs.
- AC: Fallback chains proven with chaos tests; offline/dev mode works for basic flows.

Phase 4 (4 weeks): Production hardening
- Deliverables: Load/chaos tests; deployment automation; on-call docs; DR plan.
- AC: Blue/green rollout; rollback <5 min; p95 latency and error-rate SLOs met.

## 4) SPI v1.0 scope (summary)
- LLMClient: async streaming interface; ChatRequest/Message/ToolDef types; errors (LLMError, RateLimitError, ToolCallError); capability flags.
- ToolBridge: register/invoke tools; sandboxing; MCP compatibility; retries and isolation per call.
- EmbeddingsClient: batch embedding with model-hint; usage metadata.
- Tracer: OpenTelemetry spans, usage, provider metadata.

Full spec in docs/SPI_SPEC.md.

## 5) Tool Calling program
- Produce docs/TOOL_CALLING_SPEC.md with tiers:
  - Tier 1 Native: Claude/OpenAI/Bedrock-Claude
  - Tier 2 Simulated: Vertex/Azure (structured-output)
  - Tier 3 Prompt-only: Local (no native tools)
- Define failure semantics, sandboxing, and state model; MCP mapping; mid-stream tool-call handling; retries.

## 6) Streaming protocol plan
- Gateway streams SSE; adapters normalize provider streams to ChatChunk schema; buffering and backpressure; resume tokens.
- See docs/STREAMING_PROTOCOL.md.

## 7) Configuration system
- Pydantic-based models; layered overrides (defaults→env→tenant→persona→request); schema versioning; selective hot-reload.
- Example and schema in docs/CONFIG_SCHEMA.md.

## 8) Testing strategy
- L0 API contract, L1 capability, L2 statistical quality, L3 E2E, L4 chaos; CI gating and nightly suites.
- Details in docs/TESTING_STRATEGY.md.

## 9) Cost tracking design
- Per-request usage capture; pricing tables per provider; budgets and alerts; attribution per tenant/persona.
- Details in docs/COST_TRACKING_DESIGN.md.

## 10) Migration steps and repo touchpoints
- Immediate: Replace claude_code_sdk.py with direct SDK; create adapters/claude_adapter.py.
- Refactor: persona_executor_v2.py, team_execution*_*.py, sdlc_* to call SPI; keep tool_access_mapping via ToolBridge.
- Gateway: gateway/app.py (HTTP + SSE); integrate auth and quotas later in Phase 2.

## 11) Risks and mitigations
- Tool abstraction difficulty: spike first; strict tiers; fail-fast checks.
- Streaming variability: normalize early; extensive integration tests.
- Config sprawl: validated models; limited hot-reload; audit changes.
- Timeline risk: add 20% buffer each phase; Go/No-Go after 0.5.

## 12) Week-by-week (first 4 weeks)
- W1: SPI types, ChatChunk/Errors, Tracer hooks; Anthropic SDK POC; remove Node CLI.
- W2: ClaudeAdapter streaming+tools Tier 1; Gateway SSE; L0 tests.
- W3: Refactor simplest orchestrator; ToolBridge skeleton; Config models draft.
- W4: Demo parity run; bugfixes; write TOOl_CALLING_SPEC v0.9; Go/No-Go review.

## 13) Deliverables checklist
- docs/* specs; SPI package; ClaudeAdapter; Gateway (HTTP+SSE); L0 tests; refactored orchestrator; migration/runbooks.
