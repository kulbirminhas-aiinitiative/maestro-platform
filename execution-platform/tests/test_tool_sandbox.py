from fastapi.testclient import TestClient
from execution_platform.gateway.app import app

def test_fs_roundtrip(tmp_path, monkeypatch):
    client = TestClient(app)
    # write
    r = client.post("/v1/tools/invoke", json={"name":"fs_write","args":{"path":"a/b.txt","content":"hello"}})
    assert r.status_code == 200
    # read
    r = client.post("/v1/tools/invoke", json={"name":"fs_read","args":{"path":"a/b.txt"}})
    assert r.status_code == 200
    assert r.json()["result"]["content"] == "hello"


def test_fs_traversal_blocked():
    client = TestClient(app)
    r = client.post("/v1/tools/invoke", json={"name":"fs_write","args":{"path":"../../etc/passwd","content":"x"}})
    assert r.status_code == 400
