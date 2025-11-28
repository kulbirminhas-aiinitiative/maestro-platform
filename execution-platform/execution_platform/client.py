from __future__ import annotations
import asyncio
import json
from typing import AsyncIterator, Optional
import httpx

class GatewayClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip('/')
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=60)

    async def close(self) -> None:
        await self._client.aclose()

    async def stream_chat(self, messages: list[dict], *, provider: Optional[str]=None, persona_id: Optional[str]=None, requires: Optional[dict]=None, **kwargs) -> AsyncIterator[dict]:
        params = {}
        if provider:
            params["provider"] = provider
        if persona_id:
            params["personaId"] = persona_id
        body = {"messages": messages}
        if requires is not None:
            body["requires"] = requires
        body.update({k:v for k,v in kwargs.items() if v is not None})
        async with self._client.stream("POST", "/v1/chat", params=(params or None), json=body) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("event: "):
                    ev = line.split(": ",1)[1]
                elif line.startswith("data: "):
                    data = line.split("data: ",1)[1]
                    try:
                        payload = json.loads(data)
                    except Exception:
                        payload = {"raw": data}
                    yield {"event": ev, "data": payload}

    async def embeddings(self, inputs: list[str]) -> list[list[float]]:
        r = await self._client.post("/v1/embeddings", json={"input": inputs})
        r.raise_for_status()
        data = r.json()["data"]
        return [item["embedding"] for item in data]

    async def invoke_tool(self, name: str, args: dict) -> dict:
        r = await self._client.post("/v1/tools/invoke", json={"name": name, "args": args})
        r.raise_for_status()
        return r.json()["result"]

    async def capabilities(self) -> dict:
        r = await self._client.get("/v1/capabilities")
        r.raise_for_status()
        return r.json()
