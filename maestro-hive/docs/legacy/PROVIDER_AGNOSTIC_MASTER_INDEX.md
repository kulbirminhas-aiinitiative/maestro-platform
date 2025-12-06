# Provider-Agnostic Maestro: Master Index (Start Here)

Purpose: Single entry point to plan, design, and execute the provider-agnostic SDK + Gateway initiative.

Quick start
1) Read plan: PROVIDER_AGNOSTIC_SDK_AND_GATEWAY_PLAN.md
2) Review feedback response: AGENT3_SDK_FEEDBACK_ACTION_PLAN.md
3) Execute Phase 0 Week 1 tasks from the action plan

Core documents (in recommended reading/execution order)
- PROVIDER_AGNOSTIC_SDK_AND_GATEWAY_PLAN.md — Architecture, roadmap, migration, risks
- AGENT3_SDK_FEEDBACK_ACTION_PLAN.md — Revised plan addressing AGENT3 feedback
- docs/SPI_SPEC.md — SPI v1.0 types, errors, capabilities, streaming semantics
- docs/TOOL_CALLING_SPEC.md — Tiered tool calling model, sandboxing, lifecycle, MCP mapping
- docs/STREAMING_PROTOCOL.md — Gateway SSE, normalization, backpressure, resume
- docs/CAPABILITIES_MATRIX.md — Provider capabilities for routing and persona fit
- docs/CONFIG_SCHEMA.md — Validated, layered configuration schema and examples
- docs/TESTING_STRATEGY.md — L0–L4 testing, CI gating, nightly and staging plans
- docs/COST_TRACKING_DESIGN.md — Usage capture, pricing tables, budgets, dashboards

Execution checklist (Phase 0 focus)
- Replace claude_code_sdk CLI with native Anthropic SDK
- Implement SPI package skeleton + ClaudeAdapter
- Minimal HTTP Gateway with SSE
- L0 API contract tests green
- Refactor one simple orchestrator to SPI

Repository touchpoints
- Replace: claude_code_sdk.py (direct SDK)
- Add: maestro_sdk/, adapters/, gateway/, docs/
- Refactor: persona_executor_v2.py, team_execution*_*.py, sdlc_*

Governance
- Go/No-Go after Phase 0.5 validation; feature flags for gradual rollout; blue/green for production.
