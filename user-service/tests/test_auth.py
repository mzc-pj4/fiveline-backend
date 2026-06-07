import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key")

from app.db.session import get_db
from app.main import app
from app.models.user import User

client = TestClient(app)


def make_mock_db(user=None):
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute.return_value = result
    return db


def override_db(user=None):
    def _get_db():
        yield make_mock_db(user)
    return _get_db


def test_login_success():
    from app.core.security import hash_password
    mock_user = User(
        id=1,
        email="test@test.com",
        password_hash=hash_password("password123"),
        name="테스트",
        role="customer",
    )
    app.dependency_overrides[get_db] = override_db(mock_user)

    response = client.post("/api/auth/login", json={
        "email": "test@test.com",
        "password": "password123"
    })

    assert response.status_code == 200
    assert "access_token" in response.json()
    app.dependency_overrides.clear()


def test_login_fail_wrong_password():
    from app.core.security import hash_password
    mock_user = User(
        id=1,
        email="test@test.com",
        password_hash=hash_password("password123"),
        name="테스트",
        role="customer",
    )
    app.dependency_overrides[get_db] = override_db(mock_user)

    response = client.post("/api/auth/login", json={
        "email": "test@test.com",
        "password": "wrongpassword"
    })

    assert response.status_code == 401
    app.dependency_overrides.clear()


def test_login_fail_user_not_found():
    app.dependency_overrides[get_db] = override_db(None)

    response = client.post("/api/auth/login", json={
        "email": "notexist@test.com",
        "password": "password123"
    })

    assert response.status_code == 401
    app.dependency_overrides.clear()
