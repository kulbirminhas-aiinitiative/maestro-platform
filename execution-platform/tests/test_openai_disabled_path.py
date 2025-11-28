from fastapi.testclient import TestClient
from execution_platform.gateway.app import app

def test_openai_disabled_path_no_keys():
    client = TestClient(app)
    with client.stream('POST','/v1/chat?provider=openai', json={'messages':[{'role':'user','content':'hi'}]}) as r:
        events = [ (ln.decode() if isinstance(ln,(bytes,bytearray)) else ln) for ln in r.iter_lines() if ln ]
    assert any('openai' in e for e in events)
