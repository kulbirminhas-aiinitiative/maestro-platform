from __future__ import annotations
from typing import AsyncIterator
from execution_platform.maestro_sdk.types import ChatRequest, ChatChunk, Usage
from execution_platform.maestro_sdk.interfaces import LLMClient

class ClaudeAgentAdapter(LLMClient):
    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        # Lazy import to avoid hard dependency
        try:
            # Try importing the shared SDK from maestro-hive
            import sys, os
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            hive_path = os.path.join(root, "maestro-hive")
            if hive_path not in sys.path:
                sys.path.append(hive_path)
            from claude_code_sdk import query, ClaudeCodeOptions  # type: ignore
        except Exception:
            # Fallback: emit text indicating disabled
            last = next((m for m in reversed(req.messages) if m.role == "user"), None)
            text = last.content if last else "ok"
            yield ChatChunk(delta_text=f"[claude-agent-sdk-unavailable] {text}")
            yield ChatChunk(finish_reason="stop", usage=Usage())
            return

        # Build a single prompt from messages (simple fallback behavior)
        sys_prompt = (req.system or "").strip()
        conv = []
        if sys_prompt:
            conv.append(f"[system]\n{sys_prompt}\n")
        for m in req.messages:
            role = m.role
            conv.append(f"[{role}]\n{m.content}\n")
        prompt = "\n".join(conv)

        opts = ClaudeCodeOptions()
        opts.max_tokens = req.max_tokens or 4096
        opts.temperature = req.temperature or 0.7
        # Stream results
        async for msg in query(prompt, opts):
            if msg.message_type == "text" and msg.content:
                yield ChatChunk(delta_text=msg.content)
        yield ChatChunk(finish_reason="stop", usage=Usage())
