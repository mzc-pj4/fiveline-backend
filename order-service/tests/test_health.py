import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routes.health import router

test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "order-service"
