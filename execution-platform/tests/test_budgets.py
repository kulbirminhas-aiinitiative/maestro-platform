from fastapi.testclient import TestClient
from importlib import reload

def test_token_budget_blocks(monkeypatch):
    monkeypatch.setenv('EP_TOKENS_BUDGET_PER_MINUTE', '1')
    import execution_platform.config as cfg
    reload(cfg)
    import execution_platform.gateway.app as appmod
    reload(appmod)
    client = TestClient(appmod.app)
    # First should pass
    with client.stream('POST','/v1/chat?personaId=budgeter', json={'messages':[{'role':'user','content':'hi there'}]}) as r:
        pass
    # Second should 429
    r = client.post('/v1/chat?personaId=budgeter', json={'messages':[{'role':'user','content':'ok'}]})
    assert r.status_code == 429
