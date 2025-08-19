from fastapi.testclient import TestClient

from .main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Groceries List Manager API",
        "docs": "/docs",
        "version": "1.0.0"
    }
    