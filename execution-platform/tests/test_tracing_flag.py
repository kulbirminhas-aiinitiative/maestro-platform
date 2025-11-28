from fastapi.testclient import TestClient
from importlib import reload

def test_tracing_flag_noop(monkeypatch):
    monkeypatch.setenv('EP_ENABLE_TRACING', '1')
    import execution_platform.config as cfg
    reload(cfg)
    import execution_platform.gateway.app as appmod
    reload(appmod)
    client = TestClient(appmod.app)
    with client.stream('POST','/v1/chat', json={'messages':[{'role':'user','content':'hi'}]}) as r:
        pass
