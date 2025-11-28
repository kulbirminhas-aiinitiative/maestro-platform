Tool Calling Specification (Tiered)
- Tier 1: Native tools (Claude/OpenAI)
- Tier 2: Structured output simulation (Gemini)
- Tier 3: Prompt only (local)
Contracts
- Tools declared via ToolDefinition; providers map natively or simulate.
- Fail-fast when required tools unsupported by provider.
