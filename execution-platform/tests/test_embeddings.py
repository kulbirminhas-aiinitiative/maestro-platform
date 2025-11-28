from fastapi.testclient import TestClient
from execution_platform.gateway.app import app

def test_embeddings_basic():
    client = TestClient(app)
    r = client.post('/v1/embeddings', json={'input': ['a', 'bb', 'ccc']})
    assert r.status_code == 200
    data = r.json()['data']
    assert len(data) == 3
    assert all('embedding' in item for item in data)
    assert all(len(item['embedding']) == 3 for item in data)
