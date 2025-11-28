from fastapi.testclient import TestClient
import os
from execution_platform.gateway.app import app

def test_auto_routes_to_mock_when_no_keys(monkeypatch):
    monkeypatch.delenv('EP_OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('EP_ANTHROPIC_API_KEY', raising=False)
    client = TestClient(app)
    with client.stream('POST','/v1/chat?provider=auto', json={'messages':[{'role':'user','content':'hi'}]}) as r:
        text = ''.join([(ln.decode() if isinstance(ln,(bytes,bytearray)) else ln) for ln in r.iter_lines()])
    assert 'event: token' in text or 'event: done' in text
