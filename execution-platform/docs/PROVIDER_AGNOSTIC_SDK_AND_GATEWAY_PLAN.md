Provider-Agnostic SDK and Gateway Plan (Aligned to SDK Feedback)

Decisions
- Treat claude_agent_sdk as a distinct provider (temporary).
- Persona-level routing with capability checks.
- SPI-first: src/execution_platform/spi.py (async streaming only).
- Phase-in direct Anthropic SDK later to remove CLI dependency.

Phases
0) Foundation: SPI, router, capabilities matrix, persona policy (DONE)
0.5) Validation: stub ClaudeAgent, minimal OpenAI/Gemini chat (DONE)
1) Tool calling spec and simulation layers (TBD)
2) Provider parity + error model (TBD)
3) Orchestrator migration (persona-by-persona) (TBD)
