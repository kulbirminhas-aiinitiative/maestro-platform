from fastapi.testclient import TestClient
import json
from execution_platform.gateway.app import app
from execution_platform.maestro_sdk.tool_bridge import tool_bridge

def parse_events(lines):
    events = []
    cur = None
    for ln in lines:
        s = ln.decode() if isinstance(ln,(bytes,bytearray)) else ln
        if s.startswith('event: '):
            cur = {'event': s.split(': ',1)[1].strip(), 'data': ''}
        elif s.startswith('data: '):
            if cur is not None:
                cur['data'] = s.split('data: ',1)[1]
                events.append(cur)
                cur=None
    return events

def test_tool_call_conformance_arguments_and_result():
    # tool returns its args for verification
    tool_bridge.register('return_args', lambda args, ctx: {'args': args})
    client = TestClient(app)
    body = {"messages":[{"role":"user","content":"CALL_TOOL: return_args"}],
            "tools":[{"name":"return_args","json_schema":{"type":"object","properties":{"text":{"type":"string"}}}}],
            "tool_choice":"auto"}
    with client.stream('POST','/v1/chat', json=body) as r:
        events = parse_events(list(r.iter_lines()))
    call = next(e for e in events if e['event']=='tool_call')
    result = next(e for e in events if e['event']=='tool_result')
    call_payload = json.loads(call['data'])
    result_payload = json.loads(result['data'])
    assert call_payload['type']=='tool_call' and call_payload['data']['name']=='return_args'
    assert result_payload['type']=='tool_result'
    assert result_payload['data']['args']=={"text":"hi"}
