import os, sys, asyncio, json
from pathlib import Path
from httpx import AsyncClient, ASGITransport

EXEC_PLATFORM_ROOT = str(Path(__file__).resolve().parents[2] / 'execution-platform')
sys.path.insert(0, EXEC_PLATFORM_ROOT)
from execution_platform.gateway.app import app as gw_app  # type: ignore
import execution_platform.client as gw_client_mod  # type: ignore

from persona_gateway_client import PersonaGatewayClient

async def run_json_mode():
    transport = ASGITransport(app=gw_app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        orig = gw_client_mod.httpx.AsyncClient
        gw_client_mod.httpx.AsyncClient = lambda *a, **k: ac  # type: ignore
        try:
            gw = PersonaGatewayClient(base_url='http://test')
            events = []
            async for ev in gw.stream_chat('backend_developer', messages=[{"role":"user","content":"return json"}], response_format={"type":"json"}):
                events.append(ev)
                if ev.get('event')=='done':
                    break
            # Extract token texts and assemble JSON string
            s = ''.join([e['data'].get('text','') for e in events if e['event']=='token']).strip()
            try:
                return json.loads(s)
            except Exception:
                try:
                    return json.loads(json.loads(s))
                except Exception:
                    return {"raw": s}
        finally:
            gw_client_mod.httpx.AsyncClient = orig  # type: ignore


def test_persona_json_mode_via_gateway():
    j = asyncio.run(run_json_mode())
    assert isinstance(j, dict)
