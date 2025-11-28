from fastapi.testclient import TestClient
from execution_platform.gateway.app import app

def test_streaming_contract_token_and_done():
    client = TestClient(app)
    payload = {"messages": [{"role": "user", "content": "hello world"}]}
    with client.stream("POST", "/v1/chat", json=payload) as r:
        events = list(filter(None, (line.decode() if isinstance(line, (bytes, bytearray)) else line for line in r.iter_lines())))
    assert any("event: token" in e for e in events)
    assert any("event: done" in e for e in events)


def test_tool_call_flow_with_mock_tool(monkeypatch):
    from execution_platform.maestro_sdk.tool_bridge import tool_bridge
    tool_bridge.register("echo", lambda args, ctx: {"echo": args.get("text", "")})
    client = TestClient(app)
    payload = {"messages": [{"role": "user", "content": "CALL_TOOL: echo"}]}
    with client.stream("POST", "/v1/chat", json=payload) as r:
        events = [ (line.decode() if isinstance(line, (bytes, bytearray)) else line) for line in r.iter_lines() if line ]
    assert any("event: tool_call" in e for e in events)
    assert any("event: tool_result" in e for e in events)
    assert any("\"tool_result\"" in e or "\"echo\"" in e for e in events)
