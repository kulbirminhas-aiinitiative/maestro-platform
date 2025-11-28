from __future__ import annotations
from typing import AsyncIterator
from execution_platform.maestro_sdk.types import ChatRequest, ChatChunk, Usage
from execution_platform.maestro_sdk.interfaces import LLMClient

from execution_platform.config import settings
try:
    from openai import AsyncOpenAI  # type: ignore
except Exception:
    AsyncOpenAI = None  # type: ignore

class OpenAIAdapter(LLMClient):
    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        if AsyncOpenAI is None or not getattr(settings, 'openai_api_key', None):
            last = next((m for m in reversed(req.messages) if m.role == "user"), None)
            text = last.content if last else "ok"
            yield ChatChunk(delta_text=f"[openai-disabled] {text}")
            yield ChatChunk(finish_reason="stop", usage=Usage())
            return
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        # Map messages
        msgs = [{"role": m.role, "content": m.content} for m in req.messages if m.role in ("user", "assistant")]
        # Tools (functions)
        tools = None
        if req.tools:
            tools = [{"type":"function","function":{"name": t.name, "description": t.description or "", "parameters": t.json_schema or {"type":"object","properties":{}}}} for t in req.tools]
        # tool_choice invalid when no tools
        tool_choice = (req.tool_choice or "auto") if tools else None
        # Streaming completions (removed [openai] prefix for cleaner output)
        stream = await client.chat.completions.create(
            model=getattr(settings, 'openai_model', 'gpt-4o-mini'),
            messages=msgs,
            temperature=req.temperature,
            stream=True,
            tools=tools,
            tool_choice=tool_choice,
            response_format=(req.response_format if req.response_format else None),
            max_tokens=req.max_tokens,
        )
        # Accumulate tool arguments by index
        arg_buf: dict[int, str] = {}
        name_buf: dict[int, str] = {}
        async for ev in stream:
            choice = ev.choices[0]
            delta = getattr(choice, 'delta', None)
            # Finish reason may indicate tool_calls at end
            finish = getattr(choice, 'finish_reason', None)
            if delta is None and not finish:
                continue
            # Tool call deltas
            tcs = getattr(delta, 'tool_calls', None) if delta else None
            if tcs:
                for tc in tcs:
                    idx = getattr(tc, 'index', 0)
                    fn = tc.function
                    if getattr(fn, 'name', None):
                        name_buf[idx] = fn.name
                        from execution_platform.maestro_sdk.types import ToolCall
                        yield ChatChunk(tool_call_delta=ToolCall(id=str(idx), name=fn.name, arguments={}))
                    if getattr(fn, 'arguments', None):
                        arg_buf[idx] = arg_buf.get(idx, '') + fn.arguments
                continue
            # Text deltas
            if delta and getattr(delta, 'content', None):
                yield ChatChunk(delta_text=delta.content)
            # End of stream: emit tool_complete for any pending tool calls
            if finish in ("tool_calls", "stop") and (arg_buf or name_buf):
                import json as _json
                from execution_platform.maestro_sdk.types import ToolCall
                for idx, nm in name_buf.items():
                    args_str = arg_buf.get(idx, '{}')
                    try:
                        args = _json.loads(args_str)
                    except Exception:
                        args = {}
                    yield ChatChunk(tool_call_delta=ToolCall(id=str(idx), name=nm, arguments=args), provider_events={"tool_complete": True})
        yield ChatChunk(finish_reason="stop", usage=Usage())
