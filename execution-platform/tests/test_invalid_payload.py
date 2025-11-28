from fastapi.testclient import TestClient
from execution_platform.gateway.app import app

def test_invalid_payload_missing_messages():
    client = TestClient(app)
    r = client.post("/v1/chat", json={})
    assert r.status_code == 422
