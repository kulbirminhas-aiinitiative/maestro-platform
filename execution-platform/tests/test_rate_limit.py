from fastapi.testclient import TestClient

def test_rate_limit_persona(monkeypatch):
    monkeypatch.setenv('EP_RATE_LIMIT_PER_PERSONA', '3')
    from importlib import reload
    import execution_platform.config as cfg
    reload(cfg)
    import execution_platform.gateway.app as appmod
    reload(appmod)
    client = TestClient(appmod.app)
    ok = 0
    for i in range(3):
        with client.stream('POST','/v1/chat?personaId=tester', json={'messages':[{'role':'user','content':'hi'}]}) as r:
            ok += 1
    assert ok == 3
    r = client.post('/v1/chat?personaId=tester', json={'messages':[{'role':'user','content':'hi'}]})
    assert r.status_code == 429
