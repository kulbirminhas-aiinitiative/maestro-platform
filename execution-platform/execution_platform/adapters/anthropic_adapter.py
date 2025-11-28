from __future__ import annotations
from typing import AsyncIterator
from execution_platform.maestro_sdk.types import ChatRequest, ChatChunk, Usage
from execution_platform.maestro_sdk.interfaces import LLMClient
from execution_platform.config import settings

try:
    import anthropic  # type: ignore
except Exception:  # pragma: no cover
    anthropic = None  # fallback if SDK not installed

class AnthropicAdapter(LLMClient):
    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        if anthropic is None or not settings.anthropic_api_key:
            last = next((m for m in reversed(req.messages) if m.role == "user"), None)
            text = last.content if last else "ok"
            yield ChatChunk(delta_text=f"[anthropic-disabled] {text}")
            yield ChatChunk(finish_reason="stop", usage=Usage())
            return
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        sys_prompt = req.system or None
        msgs = [{"role": m.role, "content": m.content} for m in req.messages if m.role in ("user", "assistant")]
        tools = None
        if req.tools:
            tools = [
                {"name": t.name, "description": t.description or "", "input_schema": t.json_schema or {"type": "object", "properties": {}}}
                for t in req.tools
            ]
        tool_choice = req.tool_choice if isinstance(req.tool_choice, dict) else (req.tool_choice or "auto")
        # Accumulate tool args by id
        tool_args_buf: dict[str, str] = {}

        # Build stream parameters - only include tool_choice if tools are provided
        stream_params = {
            "model": settings.anthropic_model,
            "messages": msgs,
            "system": sys_prompt,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        if tools:
            stream_params["tools"] = tools
            stream_params["tool_choice"] = tool_choice

        async with client.messages.stream(**stream_params) as stream:
            async for event in stream:
                t = getattr(event, "type", "")
                if t == "content_block_delta":
                    delta = getattr(event, "delta", None)
                    # text
                    if delta and getattr(delta, "type", "") == "text_delta":
                        yield ChatChunk(delta_text=getattr(delta, "text", ""))
                    # tool args json delta
                    if delta and getattr(delta, "type", "") == "input_json_delta":
                        block = getattr(event, "content_block", None)
                        bid = getattr(block, "id", "") if block else ""
                        part = getattr(delta, "partial_json", "")
                        tool_args_buf[bid] = tool_args_buf.get(bid, "") + part
                elif t == "content_block_start":
                    block = getattr(event, "content_block", None)
                    if block and getattr(block, "type", "") == "tool_use":
                        name = getattr(block, "name", "")
                        from execution_platform.maestro_sdk.types import ToolCall
                        yield ChatChunk(tool_call_delta=ToolCall(id=getattr(block, "id", ""), name=name, arguments={}))
                elif t == "content_block_stop":
                    block = getattr(event, "content_block", None)
                    if block and getattr(block, "type", "") == "tool_use":
                        bid = getattr(block, "id", "")
                        args_str = tool_args_buf.get(bid, "{}")
                        import json as _json
                        try:
                            args = _json.loads(args_str) if isinstance(args_str, str) else args_str
                        except Exception:
                            args = {}
                        from execution_platform.maestro_sdk.types import ToolCall
                        yield ChatChunk(tool_call_delta=ToolCall(id=bid, name=getattr(block, "name", ""), arguments=args), provider_events={"tool_complete": True})
                elif t == "message_delta":
                    pass
                elif t == "message_stop":
                    # try to surface final usage if available
                    usage = None
                    final = getattr(stream, "final_message", None)
                    if final is not None:
                        u = getattr(final, "usage", None)
                        if u is not None:
                            usage = Usage(
                                input_tokens=getattr(u, "input_tokens", None),
                                output_tokens=getattr(u, "output_tokens", None),
                            )
                    yield ChatChunk(finish_reason="stop", usage=usage or Usage())
