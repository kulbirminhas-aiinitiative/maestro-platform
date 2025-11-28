from fastapi.testclient import TestClient
import json
from execution_platform.gateway.app import app


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


def test_sse_events_have_expected_shape():
    client = TestClient(app)
    with client.stream('POST','/v1/chat', json={'messages':[{'role':'user','content':'hello world'}]}) as r:
        events = parse_events(list(r.iter_lines()))
    assert any(e['event']=='token' for e in events)
    assert any(e['event']=='done' for e in events)
    # data is JSON
    for e in events:
        try:
            json.loads(e['data'])
        except Exception:
            # allow 'done' without data json? ensure minimal
            assert e['event']=='done'
