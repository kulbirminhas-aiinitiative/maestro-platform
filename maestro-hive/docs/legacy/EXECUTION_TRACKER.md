# Execution Platform Program Tracker

Status summary
- Phase 0 (Foundation): 80% complete
- Phase 0.5 (Validation): 0% (blocked on live keys)
- Phase 1 (Second provider + tools): 20%

Key links
- Master Index: PROVIDER_AGNOSTIC_MASTER_INDEX.md
- Rollup/Quickstart: EXECUTION_PLATFORM_ROLLUP.md
- Specs: execution-platform/docs/* (SPI_SPEC, TOOL_CALLING_SPEC, STREAMING_PROTOCOL, CAPABILITIES_MATRIX, CONFIG_SCHEMA, TESTING_STRATEGY, COST_TRACKING_DESIGN)

Milestones and tasks

[Phase 0] Foundation
- [x] Provider-agnostic Gateway (HTTP+SSE), persona routing, budgets/limits
- [x] SPI skeleton and adapters: Anthropic (native), OpenAI, Gemini, Mock
- [x] ToolBridge v1 (fs_read, fs_write)
- [x] PersonaGatewayClient integration in hive (opt-in via HIVE_USE_GATEWAY)
- [x] Poetry setup; tests green
- [x] Core docs/specs + Master Index
- [ ] Remove Claude CLI path in hive (make gateway default + flag for rollback)
- [ ] Capability-aware checks in router (fail-fast when persona requires tools not supported)

[Phase 0.5] Validation (requires live keys)
- [x] Map external keys to EP_*.env and auto-load Settings
- [ ] Live smoke: Anthropic/OpenAI/Gemini parity run
- [ ] Latency/cost/error report; gap log; Go/No-Go

[Phase 1] Second provider + tool abstraction
- [ ] Tiered tool calling across providers (implement per TOOL_CALLING_SPEC)
- [ ] ProviderRouter v1 with layered config (Pydantic)
- [ ] Refactor one orchestrator fully to SPI-only path
- [ ] L1 capability tests in CI

[Phase 2] Enterprise readiness
- [ ] Observability: OTel spans/metrics/logs end-to-end
- [ ] Cost tracking service + pricing tables + budgets UI
- [ ] Circuit breakers/fallback chains
- [ ] Secrets management integration
- [ ] Runbooks and SLOs

[Phase 3] Advanced providers/routing
- [ ] Bedrock adapter; Local adapter (Tier 3 best-effort)
- [ ] A/B testing, caching, batch APIs

[Phase 4] Production hardening
- [ ] Load/chaos tests; blue/green deploy; rollback procedure

Today’s next actions
- Implement capability-aware routing/enforcement in Gateway/router.
- Prepare removal plan for Claude CLI path in hive (feature flag + migration doc).

Blockers
- Live provider keys for validation and cost/latency measurements.
