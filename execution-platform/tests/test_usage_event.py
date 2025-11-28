from fastapi.testclient import TestClient
from execution_platform.gateway.app import app

def test_usage_event_emitted():
    client = TestClient(app)
    with client.stream('POST','/v1/chat', json={'messages':[{'role':'user','content':'hi there'}]}) as r:
        events = [ (ln.decode() if isinstance(ln,(bytes,bytearray)) else ln) for ln in r.iter_lines() if ln ]
    assert any('event: usage' in e for e in events)
    assert any('event: done' in e for e in events)
