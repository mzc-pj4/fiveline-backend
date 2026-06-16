"""
Health endpoint smoke test for product-service.

Does NOT import app.main or app.db.session — only the health router is imported,
so no real DB connection is needed.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.health import router


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_health(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "product-service"
