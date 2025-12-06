# SPI v1.0 Specification (Maestro)

Status: Draft v1.0

Types (Python reference):

- Message: {role: "system"|"user"|"assistant"|"tool", content: str|[Part], name?: str, tool_call_id?: str}
- ToolDefinition: {name: str, description?: str, json_schema: dict}
- ChatRequest: {messages: list[Message], tools?: list[ToolDefinition], tool_choice?: "auto"|"none"|{name}, system?: str, temperature?: float, max_tokens?: int, stop?: list[str], response_format?: {type: "text"|"json"}, metadata?: dict}
- Usage: {input_tokens?: int, output_tokens?: int, cached_input_tokens?: int, cost_usd?: float}
- ToolCall: {id: str, name: str, arguments: dict}
- ChatChunk: {delta_text?: str, tool_call_delta?: ToolCall, finish_reason?: str, usage?: Usage, provider_events?: dict}

Errors:
- LLMError(base), RateLimitError, TimeoutError, ToolCallError, ValidationError, ProviderError

Interfaces:
- LLMClient: async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]
- ToolBridge: def register(self, tool: ToolDefinition) -> str; async def invoke(self, id: str, args: dict, ctx: dict) -> dict
- EmbeddingsClient: async def embed(self, inputs: list[str], model_hint?: str) -> list[list[float]]
- Tracer: def start_span(...); def end_span(...); context propagation hooks

Capabilities:
- {system_prompt, tool_calling, json_mode, vision, streaming, long_context, reasoning, logprobs}

Streaming semantics:
- Always return AsyncIterator[ChatChunk]; for non-streaming providers, yield one final chunk.

Versioning:
- SPI version header in Gateway; adapters declare supported SPI versions.
