from fastapi.testclient import TestClient
from execution_platform.gateway.app import app
from execution_platform.maestro_sdk.tool_bridge import tool_bridge

def test_tool_error_emits_error_event():
    def failing(args, ctx):
        raise RuntimeError("boom")
    tool_bridge.register("explode", failing)
    client = TestClient(app)
    payload = {"messages": [{"role": "user", "content": "CALL_TOOL: explode"}]}
    with client.stream("POST", "/v1/chat", json=payload) as r:
        events = [ (line.decode() if isinstance(line, (bytes, bytearray)) else line) for line in r.iter_lines() if line ]
    assert any("event: tool_call" in e for e in events)
    assert any("event: error" in e for e in events)
    assert any("boom" in e for e in events)
