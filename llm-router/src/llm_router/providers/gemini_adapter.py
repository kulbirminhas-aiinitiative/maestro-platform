from __future__ import annotations
import asyncio
import os
from typing import AsyncIterator
import google.generativeai as genai
from ..spi import LLMClient, ChatRequest, ChatChunk

class GeminiClient(LLMClient):
    def __init__(self, model: str = "gemini-1.5-flash"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self._model_name = model

    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        # google-generativeai lacks true async; run in thread to keep SPI
        def _run():
            model = genai.GenerativeModel(req.model or self._model_name)
            contents = []
            for m in req.messages:
                role = "user" if m.role != "system" else "user"
                contents.append({"role": role, "parts": [m.content]})
            resp = model.generate_content(contents)
            return resp.text or ""
        import asyncio
        text = await asyncio.to_thread(_run)
        yield ChatChunk(delta_text=text, finish_reason="stop")
