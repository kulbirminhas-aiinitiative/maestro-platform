from fastapi.testclient import TestClient
from execution_platform.gateway.app import app

def test_chat_accepts_tools_payload():
    client = TestClient(app)
    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "tools": [{"name": "sum", "description": "add", "json_schema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}}}],
        "tool_choice": "auto",
    }
    with client.stream("POST", "/v1/chat", json=payload) as r:
        assert r.status_code == 200
        # Just ensure we get a stream back
        first = next(r.iter_lines())
        assert first is not None
