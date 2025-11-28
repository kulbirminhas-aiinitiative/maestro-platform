import os, sys, asyncio
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Import in-process Gateway app
EXEC_PLATFORM_ROOT = str(Path(__file__).resolve().parents[2] / 'execution-platform')
sys.path.insert(0, EXEC_PLATFORM_ROOT)
from execution_platform.gateway.app import app as gw_app  # type: ignore
import execution_platform.client as gw_client_mod  # type: ignore

from persona_executor_v2 import PersonaExecutorV2

async def run_persona(persona_id: str, tmp_dir: Path):
    transport = ASGITransport(app=gw_app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        orig = gw_client_mod.httpx.AsyncClient
        gw_client_mod.httpx.AsyncClient = lambda *a, **k: ac  # type: ignore
        try:
            os.environ['HIVE_USE_GATEWAY'] = '1'
            os.environ.setdefault('GATEWAY_URL', 'http://test')
            ex = PersonaExecutorV2(persona_id=persona_id, output_dir=tmp_dir)
            return await ex.execute(requirement=f'{persona_id} quick task', contract=None, context=None, use_mock=False)
        finally:
            gw_client_mod.httpx.AsyncClient = orig  # type: ignore


def test_backend_and_qa_personas_via_gateway(tmp_path):
    res1 = asyncio.run(run_persona('backend_developer', tmp_path / 'b'))
    res2 = asyncio.run(run_persona('qa_engineer', tmp_path / 'q'))
    assert res1.success and res2.success
