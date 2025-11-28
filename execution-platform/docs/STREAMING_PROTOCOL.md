Streaming protocol (SSE)

Events
- token: { text }
- tool_call: { type: "tool_call", data: { name, args } }
- tool_result: { type: "tool_result", data: any }
- usage: { input_tokens?, output_tokens?, cost_usd }
- done: { reason, usage? }
- error: { error }

Notes
- tool_result is emitted only after provider signals tool_complete
- JSON mode may stream JSON as text tokens; clients should assemble and parse
