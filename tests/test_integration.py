from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sum_endpoint():
    response = client.post("/sum", json={"a": 12, "b": 30})
    assert response.status_code == 200
    assert response.json() == {"result": 42}


def test_sum_validation():
    response = client.post("/sum", json={"a": "not-a-number", "b": 1})
    assert response.status_code == 422
