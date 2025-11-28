import os, json
import pytest
from fastapi.testclient import TestClient
from execution_platform.gateway.app import app

@pytest.mark.skipif(not os.environ.get('EP_ANTHROPIC_API_KEY'), reason='No Anthropic key')
def test_live_anthropic_stream_smoke():
    client = TestClient(app)
    with client.stream('POST','/v1/chat?provider=anthropic', json={'messages':[{'role':'user','content':'Say "ok"'}]}) as r:
        events = [ (ln.decode() if isinstance(ln,(bytes,bytearray)) else ln) for ln in r.iter_lines() if ln ]
    assert any('event: token' in e for e in events)
    assert any('event: done' in e for e in events)

@pytest.mark.skipif(not os.environ.get('EP_OPENAI_API_KEY'), reason='No OpenAI key')
def test_live_openai_stream_smoke():
    client = TestClient(app)

@pytest.mark.skipif(not os.environ.get('EP_GEMINI_API_KEY'), reason='No Gemini key')
def test_live_gemini_smoke():
    client = TestClient(app)
    with client.stream('POST','/v1/chat?provider=gemini', json={'messages':[{'role':'user','content':'Say "ok"'}]}) as r:
        events = [ (ln.decode() if isinstance(ln,(bytes,bytearray)) else ln) for ln in r.iter_lines() if ln ]
    assert any('event: token' in e for e in events or []) or any('event: done' in e for e in events)

    with client.stream('POST','/v1/chat?provider=openai', json={'messages':[{'role':'user','content':'Say "ok"'}]}) as r:
        events = [ (ln.decode() if isinstance(ln,(bytes,bytearray)) else ln) for ln in r.iter_lines() if ln ]
    assert any('event: token' in e for e in events)
    assert any('event: done' in e for e in events)
