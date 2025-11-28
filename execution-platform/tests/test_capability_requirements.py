from fastapi.testclient import TestClient
from importlib import reload

def test_requirements_enforced():
    import execution_platform.gateway.app as appmod
    client = TestClient(appmod.app)
    r = client.post('/v1/chat?provider=mock', json={
        'messages':[{'role':'user','content':'hi'}],
        'response_format': None,
        'tools': None,
        'tool_choice': None,
        'requires': {'tool_calling':'native'}
    })
    assert r.status_code == 412
