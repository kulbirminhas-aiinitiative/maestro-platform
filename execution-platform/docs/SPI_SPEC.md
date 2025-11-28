SPI Spec (summary)

Types
- ChatRequest: messages[{role,content}], system?, tools?, tool_choice?, response_format?, max_tokens?, temperature?
- ChatChunk: delta_text?, tool_call_delta?{id,name,arguments}, usage?{input_tokens?,output_tokens?,cost_usd?}, finish_reason?, provider_events?

Interfaces
- LLMClient.chat(req) -> AsyncIterator[ChatChunk]
- ToolBridge.register(name, fn), invoke(name,args,ctx)
- EmbeddingsClient.embed(inputs, model_hint?) -> list[list[float]]

Adapters must map provider streaming/tool outputs to ChatChunk semantics.
