# Tool Calling Specification

Goals: portable, safe, and debuggable tool execution across providers.

Tiers:
- Tier 1 (Native): providers with first-class tool/function calling. Exact JSON schema mapping.
- Tier 2 (Simulated): providers with structured output only; tool calls simulated via constrained JSON responses + dispatcher.
- Tier 3 (Prompt-only): no structured support; tools invoked via ReAct-style prompting; limited reliability; not for critical personas.

State model:
- Tools are stateless functions; stateful effects (FS, Bash) are sandboxed by ToolBridge.
- Each tool call carries execution context (cwd, tenant, session, timebox, permissions).

Lifecycle:
1) Model proposes tool_call{name,args} (native or simulated)
2) Gateway pauses model stream; ToolBridge invokes tool with isolation and timeout
3) Tool result returned as tool message; streaming resumes
4) Errors encoded as tool_error events; retry policy applied per tool

Sandboxing:
- FS: chroot/workspace dir per session; allowlist operations; quota on bytes written
- Bash: restricted shell, resource limits, network off by default
- Web: outbound HTTP allowlist; redact secrets

Failure semantics:
- Tool failure → assistant receives error summary; router may switch provider only on model-side errors, not tool-side

Telemetry:
- Trace spans per tool, args (redacted) fingerprint, duration, exit code, bytes read/written

MCP:
- Map MCP tools to ToolBridge; enforce schema compatibility; adapter per MCP server
