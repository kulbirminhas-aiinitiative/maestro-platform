from __future__ import annotations
from typing import AsyncIterator, Protocol
from .types import ChatRequest, ChatChunk

class LLMClient(Protocol):
    async def chat(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        ...

class ToolBridge(Protocol):
    async def invoke(self, name: str, args: dict, ctx: dict) -> dict:
        ...

class EmbeddingsClient(Protocol):
    async def embed(self, inputs: list[str], model_hint: str | None = None) -> list[list[float]]:
        ...
