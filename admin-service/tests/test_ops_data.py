import json
import os
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import CurrentUser, require_admin
from app.routes.dashboard import router


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_admin] = lambda: CurrentUser(user_id=1, role="admin")
    return TestClient(app)


def test_ops_data_no_bucket(client: TestClient):
    with patch.dict(os.environ, {"DASHBOARD_BUCKET": ""}):
        r = client.get("/api/admin/ops-data")
    assert r.status_code == 503


def test_ops_data_success(client: TestClient):
    payload = {"generatedAt": "2026-06-19", "summary": {}}
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps(payload).encode()
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": mock_body}

    with patch.dict(os.environ, {"DASHBOARD_BUCKET": "test-bucket"}):
        with patch("boto3.client", return_value=mock_s3):
            r = client.get("/api/admin/ops-data")

    assert r.status_code == 200
    assert r.json()["generatedAt"] == "2026-06-19"


def test_ops_data_key_not_found(client: TestClient):
    error_resp = {"Error": {"Code": "NoSuchKey", "Message": "not found"}}
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = ClientError(error_resp, "GetObject")

    with patch.dict(os.environ, {"DASHBOARD_BUCKET": "test-bucket"}):
        with patch("boto3.client", return_value=mock_s3):
            r = client.get("/api/admin/ops-data")

    assert r.status_code == 404


def test_ops_data_s3_error(client: TestClient):
    error_resp = {"Error": {"Code": "InternalError", "Message": "S3 error"}}
    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = ClientError(error_resp, "GetObject")

    with patch.dict(os.environ, {"DASHBOARD_BUCKET": "test-bucket"}):
        with patch("boto3.client", return_value=mock_s3):
            r = client.get("/api/admin/ops-data")

    assert r.status_code == 503
