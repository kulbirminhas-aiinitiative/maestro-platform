from __future__ import annotations
import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time
from collections import defaultdict, deque
from typing import Deque, Tuple
from execution_platform.telemetry import span, record_event

# CORS configuration from environment
_CORS_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _CORS_ORIGINS.split(",")]
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncIterator
from execution_platform.config import settings
from execution_platform.maestro_sdk.router import get_adapter
from execution_platform.maestro_sdk.types import ChatRequest, Message, ChatChunk
from execution_platform.maestro_sdk.tool_bridge import tool_bridge, register_default_tools

_persona_hits: dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=1000))
_persona_token_events: dict[str, Deque[Tuple[float,int]]] = defaultdict(lambda: deque(maxlen=2000))
_persona_cost_events: dict[str, Deque[Tuple[float,float]]] = defaultdict(lambda: deque(maxlen=2000))

app = FastAPI(title=settings.app_name)
# CORS middleware - configure CORS_ALLOWED_ORIGINS env var in production
app.add_middleware(CORSMiddleware, allow_origins=CORS_ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Register default tools (fs_read/fs_write)
register_default_tools(settings.workspace_root)


class ChatMessage(BaseModel):
    role: str
    content: str

class ToolDef(BaseModel):
    name: str
    description: str | None = None
    json_schema: dict | None = None

def _within_minute_trim(q: Deque, now: float):
    while q and now - q[0][0] > 60:
        q.popleft()

class ChatBody(BaseModel):
    messages: list[ChatMessage]
    response_format: dict | None = None
    tools: list[ToolDef] | None = None
    tool_choice: dict | str | None = None
    requires: dict | None = None

async def sse(iter_chunks: AsyncIterator[ChatChunk], provider_name: str, persona_id: str | None = None):
    from execution_platform.maestro_sdk.costs import compute_cost
    async for ch in iter_chunks:
        if ch.tool_call_delta:
            ev = {"type": "tool_call", "data": {"name": ch.tool_call_delta.name, "args": ch.tool_call_delta.arguments}}
            yield f"event: tool_call\ndata: {json.dumps(ev)}\n\n"
            # Invoke tool only when adapter signals completion
            if ch.provider_events and ch.provider_events.get("tool_complete"):
                try:
                    result = await tool_bridge.invoke(ch.tool_call_delta.name, ch.tool_call_delta.arguments, ctx={})
                    yield "event: tool_result\n" + "data: " + json.dumps({"type": "tool_result", "data": result}) + "\n\n"
                except Exception as e:
                    yield "event: error\n" + "data: " + json.dumps({"error": str(e)}) + "\n\n"
            continue
        if ch.delta_text:
            yield "event: token\n" + "data: " + json.dumps({"text": ch.delta_text}) + "\n\n"
        if ch.usage and not ch.finish_reason:
            d = ch.usage.__dict__.copy()
            d["cost_usd"] = d.get("cost_usd") or compute_cost(ch.usage, provider_name)
            d["provider"] = provider_name
            # record budgets
            now = time.time()
            if persona_id:
                if d.get("input_tokens") or d.get("output_tokens"):
                    _persona_token_events[persona_id].append((now, int((d.get("input_tokens") or 0) + (d.get("output_tokens") or 0))))
                    _within_minute_trim(_persona_token_events[persona_id], now)
                _persona_cost_events[persona_id].append((now, float(d["cost_usd"])) )
                _within_minute_trim(_persona_cost_events[persona_id], now)
                # budget enforcement mid-stream
                if settings.tokens_budget_per_minute:
                    total_tokens = sum(t for _, t in _persona_token_events[persona_id])
                    if total_tokens > settings.tokens_budget_per_minute:
                        yield "event: error\n" + "data: " + json.dumps({"error": "token_budget_exceeded"}) + "\n\n"
                        return
                if settings.budget_per_minute_usd:
                    total_cost = sum(c for _, c in _persona_cost_events[persona_id])
                    if total_cost > settings.budget_per_minute_usd:
                        yield "event: error\n" + "data: " + json.dumps({"error": "cost_budget_exceeded"}) + "\n\n"
                        return
            yield "event: usage\n"
            yield "data: " + json.dumps(d) + "\n\n"
        if ch.finish_reason:
            usage = None
            if ch.usage:
                d = ch.usage.__dict__.copy()
                d["cost_usd"] = d.get("cost_usd") or compute_cost(ch.usage, provider_name)
                d["provider"] = provider_name
                usage = d
            yield "event: done\n" + "data: " + json.dumps({"reason": ch.finish_reason, "usage": usage, "provider": provider_name}) + "\n\n"

@app.get("/v1/health/providers")
async def health_providers():
    import importlib.util, os
    # Check availability of claude_agent by importing local SDK wrapper
    try:
        # Discover if maestro-hive/claude_code_sdk.py exists
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        hive_sdk = os.path.join(root, "maestro-hive", "claude_code_sdk.py")
        claude_agent_available = os.path.exists(hive_sdk)
    except Exception:
        claude_agent_available = False
    return {
        "anthropic": {"sdk": bool(importlib.util.find_spec('anthropic')), "configured": bool(settings.anthropic_api_key)},
        "openai": {"sdk": bool(importlib.util.find_spec('openai')), "configured": bool(settings.openai_api_key)},
        "gemini": {"sdk": bool(importlib.util.find_spec('google.generativeai')), "configured": bool(getattr(settings, 'gemini_api_key', None))},
        "claude_agent": {"sdk": claude_agent_available, "configured": claude_agent_available},
    }


@app.get("/v1/capabilities")
async def capabilities():
    from execution_platform.maestro_sdk.capabilities import CAPABILITIES
    provider = settings.provider
    return {"provider": provider, "capabilities": CAPABILITIES.get(provider, {})}

class ToolInvokeBody(BaseModel):
    name: str
    args: dict

@app.post("/v1/tools/invoke")
async def invoke_tool(body: ToolInvokeBody):
    try:
        result = await tool_bridge.invoke(body.name, body.args, ctx={})
        return {"ok": True, "result": result}
    except (ValueError, FileNotFoundError, KeyError) as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))

class EmbeddingsBody(BaseModel):
    input: list[str]

@app.post("/v1/embeddings")
async def embeddings(body: EmbeddingsBody, provider: str | None = None):
    # For now, use mock embeddings; provider integration later
    from execution_platform.maestro_sdk.embeddings import MockEmbeddings
    vecs = await MockEmbeddings().embed(body.input)
    return {"data": [{"index": i, "embedding": v} for i, v in enumerate(vecs)]}

@app.post("/v1/chat")
async def chat(body: ChatBody, provider: str | None = None, personaId: str | None = None):
    # Simple in-memory rate limit per persona if configured
    if settings.rate_limit_per_persona and personaId:
        now = time.time()
        window = _persona_hits[personaId]
        # remove hits older than 60 seconds
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= settings.rate_limit_per_persona:
            raise HTTPException(status_code=429, detail="Rate limit exceeded for persona")
        window.append(now)
    # Budget pre-check
    if personaId:
        now = time.time()
        if settings.tokens_budget_per_minute:
            _within_minute_trim(_persona_token_events[personaId], now)
            total_tokens = sum(t for _, t in _persona_token_events[personaId])
            if total_tokens >= settings.tokens_budget_per_minute:
                raise HTTPException(status_code=429, detail="Token budget exhausted for persona")
        if settings.budget_per_minute_usd:
            _within_minute_trim(_persona_cost_events[personaId], now)
            total_cost = sum(c for _, c in _persona_cost_events[personaId])
            if total_cost >= settings.budget_per_minute_usd:
                raise HTTPException(status_code=429, detail="Cost budget exhausted for persona")
    req = ChatRequest(
        messages=[Message(role=m.role, content=m.content) for m in body.messages],
        response_format=body.response_format,
        tools=[
            __import__('builtins').__dict__.get('dict')(
                name=t.name, description=t.description, json_schema=t.json_schema or {}
            )
            for t in (body.tools or [])
        ],
        tool_choice=body.tool_choice,
    )
    # Persona-level provider override
    prov = (provider or settings.provider)
    if personaId and settings.persona_provider_map_path:
        try:
            import json as _json, os
            map_path = settings.persona_provider_map_path
            if os.path.exists(map_path):
                with open(map_path, 'r', encoding='utf-8') as f:
                    m = _json.load(f)
                prov = m.get(personaId, prov)
        except Exception:
            pass
    # Capability-aware enforcement
    if body.requires:
        from execution_platform.maestro_sdk.requirements import ensure_requirements, RequirementError
        try:
            ensure_requirements(prov, body.requires)
        except RequirementError as e:
            raise HTTPException(status_code=412, detail=str(e))
    llm = get_adapter(prov)
    with span("gateway.chat", enabled=settings.enable_tracing, provider=prov, persona=personaId):
        return StreamingResponse(sse(llm.chat(req), prov, personaId), media_type="text/event-stream")
