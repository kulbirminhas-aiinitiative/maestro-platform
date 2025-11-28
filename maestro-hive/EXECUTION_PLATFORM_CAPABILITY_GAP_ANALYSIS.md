# Execution Platform: Capability & Gap Analysis

Summary
This document captures current capabilities, gaps, and future tasks for the provider-agnostic Execution Platform (Gateway + SPI) used by Maestro Hive personas.

References
- Master: PROVIDER_AGNOSTIC_MASTER_INDEX.md
- Tracker: EXECUTION_TRACKER.md, docs/EXECUTION_TRACKER_RUNBOOK.md
- Gateway/SPI code: /execution-platform
- Capability matrix: execution_platform/maestro_sdk/capabilities.py

Current capabilities (as of today)
- Provider abstraction (SPI): Adapters for Anthropic, OpenAI, Gemini, Mock; router supports provider=auto key-based selection.
- Streaming Gateway (FastAPI + SSE): /v1/chat, /v1/tools/invoke, /v1/embeddings (mock), /v1/health/providers, /v1/capabilities.
- Tool bridge v1: fs_read, fs_write; tool_call and usage events with ordering; end-to-end tests green.
- Persona-scoped routing: PersonaGatewayClient reads persona_config.json with provider + fallback chain per persona.
- Budget and rate limits: per-persona token/cost budgets per minute and request rate-limits; mid-stream enforcement.
- Capability-aware enforcement: body.requires field validated against CAPABILITIES; 412 returned if unmet.
- Config: EP_* env via execution-platform/.env; OpenAI/Gemini configured; Anthropic pending.
- Test coverage: 26 passed / 3 skipped locally for execution-platform (streaming, tools, budgets, router, contracts).

Gaps / limitations
- Claude Agent SDK parity: current hive still has direct Claude CLI path; Gateway is not the default path yet.
- Cross-provider tool-calling parity: only fs_* implemented; need generalized tool protocol and argument/result mapping across providers; MCP compatibility layer not yet provided.
- Provider capability surface: Gemini streaming is limited; need stream bridging and JSON/tool mode conformance tests per adapter.
- Anthropic live validation pending (no key); full 3-way parity not proven.
- Observability: OTel tracing/metrics/logs across gateway and adapters not implemented; only simple spans.
- Cost tracking: pricing tables + service with per-provider model costs and budget policies not persisted/queried.
- Secret management: relies on .env; integrate with secret store (AWS/GCP/Vault) and per-persona scoping.
- Resilience: circuit breakers, retries, fallback chains with reason tracking not formalized.
- Embeddings: mock only; need router/adapters for OpenAI/Vertex/Bedrock with tests.
- CI/CD: dedicated Poetry job for execution-platform; smoke tests with real providers; blue/green and rollback guides.
- Documentation: full SPI/Tool Calling spec hardening; provider-specific caveats; runbook for migrations in hive.

Future tasks (roadmap)
Phase 0 (finish foundation)
- Make Gateway default in hive; keep Claude path behind feature flag; migration doc and rollback procedure.
- Add capability requirements per persona in persona_config.json and enforce via body.requires.

Phase 0.5 (validation)
- Live smoke tests: OpenAI and Gemini; capture latency, token, and cost usage; generate gap log.
- Add Anthropic key and run 3-way parity tests; record deltas in a matrix.

Phase 1 (tooling & SPI hardening)
- Implement ToolBridge v2: generic tool protocol (args/result, multi-turn), provider mappings; minimal MCP-compat layer.
- Expand tools: http_fetch, code_search, dir_glob, exec_cmd (guarded), and sandbox policies; conformance tests.
- Provider capability shims: JSON mode coercion, non-stream to pseudo-stream bridge for Gemini.

Phase 2 (enterprise readiness)
- OTel tracing/metrics/logs end-to-end; dashboards and alerting; request correlation IDs.
- Cost tracking service + pricing tables; budget policies persisted; per-persona monthly budgets.
- Secret manager integration; per-persona/provider credentials; rotation runbook.
- Circuit breakers, retries, fallback chain reasoning; error taxonomy.

Phase 3 (breadth & optimization)
- Add Bedrock and Local adapters; embeddings router with vector backends.
- A/B routing, caching, batch APIs; cold start warmers; rate scheduling.

Phase 4 (prod hardening)
- Load and chaos tests; SLOs; oncall runbook; blue/green deploy and rollback validation.

Risks & mitigations
- Provider behavioral drift: maintain CI parity matrix; version-pinned adapters; integration tests per provider.
- Cost runaway: enforce budgets, alerts, and circuit breakers; preflight estimate where possible.
- Secret leakage: use secret store, avoid logs, redact events.

Action items (near-term)
- Switch hive default to Gateway; add feature flag and migration notes.
- Implement ToolBridge v2 minimal and adapter shims; add conformance tests.
- Run live smoke for OpenAI/Gemini; request Anthropic key; update tracker.
