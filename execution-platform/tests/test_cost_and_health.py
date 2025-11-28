from fastapi.testclient import TestClient
import json
from execution_platform.gateway.app import app

def test_usage_cost_present():
    client = TestClient(app)
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
    with client.stream('POST','/v1/chat', json={'messages':[{'role':'user','content':'hi there'}]}) as r:
        events = parse_events(list(r.iter_lines()))
    usage_event = next(e for e in events if e['event']=='usage')
    data = json.loads(usage_event['data'])
    assert 'cost_usd' in data and isinstance(data['cost_usd'], float)


def test_health_providers_endpoint():
    client = TestClient(app)
    r = client.get('/v1/health/providers')
    assert r.status_code == 200
    j = r.json()
    assert 'anthropic' in j and 'openai' in j
    assert 'configured' in j['anthropic'] and 'sdk' in j['openai']
