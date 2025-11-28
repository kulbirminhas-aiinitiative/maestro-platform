import asyncio
import anyio
from fastapi import FastAPI
from httpx import AsyncClient
from httpx import ASGITransport
from execution_platform.gateway.app import app
from execution_platform.client import GatewayClient

async def _collect_events(base_url: str):
    client = GatewayClient(base_url)
    events = []
    async for ev in client.stream_chat(messages=[{"role":"user","content":"hello world"}]):
        events.append(ev)
        if ev["event"] == "done":
            break
    await client.close()
    return events

async def _collect_tool_flow(base_url: str):
    client = GatewayClient(base_url)
    events = []
    async for ev in client.stream_chat(messages=[{"role":"user","content":"CALL_TOOL: echo"}]):
        events.append(ev)
        if ev["event"] == "done":
            break
    await client.close()
    return events

async def _collect_embeddings(base_url: str):
    client = GatewayClient(base_url)
    vecs = await client.embeddings(["a","bb"]) 
    await client.close()
    return vecs

async def _run_with_asgi(app: FastAPI, fn):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # patch GatewayClient to use this AsyncClient
        import execution_platform.client as cmod
        orig = cmod.httpx.AsyncClient
        cmod.httpx.AsyncClient = lambda *a, **k: ac  # type: ignore
        try:
            return await fn("http://test")
        finally:
            cmod.httpx.AsyncClient = orig  # type: ignore


def test_client_stream_and_done():
    events = anyio.run(_run_with_asgi, app, _collect_events)
    assert any(ev["event"]=="token" for ev in events)
    assert any(ev["event"]=="done" for ev in events)


def test_client_tool_flow():
    events = anyio.run(_run_with_asgi, app, _collect_tool_flow)
    kinds = [ev["event"] for ev in events]
    assert "tool_call" in kinds and "tool_result" in kinds


def test_client_embeddings():
    vecs = anyio.run(_run_with_asgi, app, _collect_embeddings)
    assert len(vecs)==2 and isinstance(vecs[0], list)
