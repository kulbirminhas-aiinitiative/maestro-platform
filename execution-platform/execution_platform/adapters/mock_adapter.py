from __future__ import annotations
import asyncio
from typing import AsyncIterator
from execution_platform.maestro_sdk.types import ChatRequest, ChatChunk, ToolCall, Usage
from execution_platform.maestro_sdk.interfaces import LLMClient

class MockAdapter(LLMClient):
    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        # JSON mode simulation
        if req.response_format and req.response_format.get("type") == "json":
            yield ChatChunk(delta_text='{"ok": true}')
            yield ChatChunk(finish_reason="stop", usage=Usage())
            return
        # Emit a fake tool call if special marker present
        last_user = next((m for m in reversed(req.messages) if m.role == "user"), None)
        if last_user and last_user.content.startswith("CALL_TOOL:"):
            _, spec = last_user.content.split(":", 1)
            name = spec.strip() or "echo"
            # announce tool
            yield ChatChunk(tool_call_delta=ToolCall(id="t1", name=name, arguments={"text": "hi"}))
            await asyncio.sleep(0)
            # signal completion for invocation
            yield ChatChunk(tool_call_delta=ToolCall(id="t1", name=name, arguments={"text": "hi"}), provider_events={"tool_complete": True})
            await asyncio.sleep(0)
            yield ChatChunk(delta_text="[tool result will follow]", finish_reason=None)
            yield ChatChunk(finish_reason="stop", usage=Usage(input_tokens=1, output_tokens=1))
            return
        # Otherwise just echo tokens
        text = (last_user.content if last_user else "ok")
        for tok in text.split():
            yield ChatChunk(delta_text=tok + " ")
            await asyncio.sleep(0)
        # emit usage before finish
        yield ChatChunk(usage=Usage(input_tokens=len(text), output_tokens=len(text)))
        yield ChatChunk(finish_reason="stop")