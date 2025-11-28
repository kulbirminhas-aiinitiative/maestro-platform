from __future__ import annotations
import math
from typing import List
from .interfaces import EmbeddingsClient

class MockEmbeddings(EmbeddingsClient):
    async def embed(self, inputs: List[str], model_hint: str | None = None) -> List[List[float]]:
        vecs = []
        for s in inputs:
            h = sum(ord(c) for c in s)
            vecs.append([math.sin(h % 1000)/2, math.cos(h % 1000)/2, len(s)])
        return vecs
