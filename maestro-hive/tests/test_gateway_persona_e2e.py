import os, sys
import asyncio
from pathlib import Path
import types

# Ensure execution-platform importable
EXEC_PLATFORM_ROOT = str(Path(__file__).resolve().parents[2] / 'execution-platform')
sys.path.insert(0, EXEC_PLATFORM_ROOT)

from execution_platform.gateway.app import app as gw_app  # type: ignore
from httpx import AsyncClient, ASGITransport  # type: ignore
import execution_platform.client as gw_client_mod  # type: ignore
from persona_executor_v2 import PersonaExecutorV2

async def run_persona(tmp_dir: Path):
    # Patch GatewayClient to use ASGI transport
    transport = ASGITransport(app=gw_app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        orig = gw_client_mod.httpx.AsyncClient
        gw_client_mod.httpx.AsyncClient = lambda *a, **k: ac  # type: ignore
        try:
            os.environ['HIVE_USE_GATEWAY'] = '1'
            os.environ.setdefault('GATEWAY_URL', 'http://test')
            ex = PersonaExecutorV2(persona_id='backend_developer', output_dir=tmp_dir)
            res = await ex.execute(requirement='Say hello world', contract=None, context=None, use_mock=False)
            return res
        finally:
            gw_client_mod.httpx.AsyncClient = orig  # type: ignore


def test_persona_e2e_gateway(tmp_path):
    res = asyncio.run(run_persona(tmp_path))
    assert res.success is True
    # No files required; ensure no crash and result returned
    assert isinstance(res.files_created, list)
