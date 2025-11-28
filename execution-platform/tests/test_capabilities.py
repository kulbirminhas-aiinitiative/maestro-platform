from fastapi.testclient import TestClient
from execution_platform.gateway.app import app

def test_capabilities_endpoint():
    client = TestClient(app)
    r = client.get("/v1/capabilities")
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] in ("mock", "anthropic")
    caps = data["capabilities"]
    assert "streaming" in caps and isinstance(caps["streaming"], bool)
    assert "tool_calling" in caps
