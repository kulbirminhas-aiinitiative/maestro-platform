from fastapi.testclient import TestClient
from execution_platform.gateway.app import app
from execution_platform.maestro_sdk.tool_bridge import tool_bridge

def test_tool_ordering_call_then_result():
    tool_bridge.register("echo2", lambda args, ctx: {"ok": True})
    client = TestClient(app)
    payload = {"messages": [{"role": "user", "content": "CALL_TOOL: echo2"}]}
    with client.stream("POST", "/v1/chat", json=payload) as r:
        events = [ (ln.decode() if isinstance(ln,(bytes,bytearray)) else ln) for ln in r.iter_lines() if ln ]
    call_idx = next(i for i,e in enumerate(events) if "event: tool_call" in e)
    result_idx = next(i for i,e in enumerate(events) if "event: tool_result" in e)
    assert call_idx < result_idx
