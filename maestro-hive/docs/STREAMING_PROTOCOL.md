# Streaming Protocol

Gateway → Client: Server-Sent Events (SSE)
- event: token | tool_start | tool_end | usage | error | done
- data: ChatChunk JSON per event type

Adapter normalization:
- Convert provider-specific streams (SSE, gRPC) into ChatChunk events
- Buffer by sentence for providers lacking token-level deltas; include offsets

Backpressure:
- Bounded buffers; drop policy: slow clients trigger paused provider stream, resume when drained

Recovery:
- Resume tokens per N chunks; if disconnect, client may reconnect with Last-Event-ID

Tool-in-stream:
- Emit tool_start; pause text deltas; run tool; emit tool_end; resume
