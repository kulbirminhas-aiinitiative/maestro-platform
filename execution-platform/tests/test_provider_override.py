from fastapi.testclient import TestClient
from execution_platform.gateway.app import app

def collect_text(lines):
    out = []
    for ln in lines:
        s = ln.decode() if isinstance(ln,(bytes,bytearray)) else ln
        if s.startswith('data:') and '"text":' in s:
            out.append(s)
    return '\n'.join(out)

def test_provider_override_openai():
    client = TestClient(app)
    with client.stream('POST','/v1/chat?provider=openai', json={'messages':[{'role':'user','content':'hello'}]}) as r:
        text = collect_text(r.iter_lines())
    assert ('[openai]' in text) or ('[openai-disabled]' in text)

def test_json_mode():
    client = TestClient(app)
    body = {"messages":[{"role":"user","content":"return json"}],"response_format":{"type":"json"}}
    with client.stream('POST','/v1/chat', json=body) as r:
        json_chunks = []
        for ln in r.iter_lines():
            s = ln.decode() if isinstance(ln,(bytes,bytearray)) else ln
            if s.startswith('data:') and '"text":' in s:
                payload = s.split('data: ',1)[1]
                obj = __import__('json').loads(payload)
                json_chunks.append(obj["text"])
    import json
    s = ''.join(json_chunks)
    # If model wrapped json in a JSON string, unquote first
    if s.startswith('"') and s.endswith('"'):
        s = json.loads(s)
    assert json.loads(s) == {"ok": True}
