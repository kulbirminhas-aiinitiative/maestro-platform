import asyncio
from execution_platform.spi import Message, ChatRequest
from execution_platform.router import PersonaRouter

async def _collect(ait):
    out = []
    async for c in ait:
        out.append(c)
    return out

def test_spi_stream_path_runs_stub():
    r = PersonaRouter()
    client = r.get_client("code_writer")
    req = ChatRequest(messages=[Message(role="user", content="hello")])
    chunks = asyncio.get_event_loop().run_until_complete(_collect(client.chat(req)))
    assert any(c.delta_text for c in chunks)
