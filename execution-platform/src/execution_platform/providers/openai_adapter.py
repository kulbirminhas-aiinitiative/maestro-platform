from __future__ import annotations
import asyncio
import os
from typing import AsyncIterator
from openai import AsyncOpenAI
from execution_platform.spi import LLMClient, ChatRequest, ChatChunk, Message

class OpenAIClient(LLMClient):
    def __init__(self, model: str = "gpt-4o-mini"):
        self._model = model
        self._client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        messages = [{"role": m.role, "content": m.content} for m in req.messages]
        stream = await self._client.chat.completions.create(
            model=req.model or self._model,
            messages=messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            stream=True,
        )
        async for ev in stream:
            delta = ev.choices[0].delta.content if ev.choices and ev.choices[0].delta else None
            if delta:
                yield ChatChunk(delta_text=delta)
        yield ChatChunk(finish_reason="stop")
        await asyncio.sleep(0)
