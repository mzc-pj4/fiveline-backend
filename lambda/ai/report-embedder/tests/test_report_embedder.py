"""
report-embedder/handler.py 테스트
- S3 마크다운 → Bedrock Titan Embed → DDB 저장 흐름
- 충돌 회피: importlib.util 로 명시적 로드
"""
import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("BUCKET_NAME", "test-bucket")
os.environ.setdefault("EMBED_TABLE", "test-embed-table")


@pytest.fixture
def hm():
    """handler.py 를 unique 이름(report_embedder_handler)으로 로드"""
    spec = importlib.util.spec_from_file_location(
        "report_embedder_handler",
        Path(__file__).parent.parent / "handler.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["report_embedder_handler"] = mod
    spec.loader.exec_module(mod)
    # boto3 객체들을 mock 으로 교체
    mod.s3 = MagicMock()
    mod.bedrock = MagicMock()
    mod.ddb = MagicMock()
    yield mod
    sys.modules.pop("report_embedder_handler", None)


def test_report_id_from_key(hm):
    assert hm.report_id_from_key("reports/daily/2026-06-22.md") == "daily-2026-06-22"


def test_list_reports_filters_md(hm):
    paginator = MagicMock()
    paginator.paginate.return_value = [{
        "Contents": [
            {"Key": "reports/daily/2026-06-22.md"},
            {"Key": "reports/daily/index.txt"},
            {"Key": "reports/daily/2026-06-21.md"},
        ]
    }]
    hm.s3.get_paginator.return_value = paginator

    result = hm.list_reports()

    assert len(result) == 2
    assert all(k.endswith(".md") for k in result)


def test_read_md_decodes_and_truncates(hm):
    long_text = "가" * 10000
    mock_body = MagicMock()
    mock_body.read.return_value = long_text.encode("utf-8")
    hm.s3.get_object.return_value = {"Body": mock_body}

    result = hm.read_md("reports/daily/test.md")

    assert len(result) <= 8000


def test_embed_text_returns_vector(hm):
    fake_vector = [0.1] * 1024
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps({"embedding": fake_vector}).encode()
    hm.bedrock.invoke_model.return_value = {"body": mock_body}

    result = hm.embed_text("테스트 문서")

    assert len(result) == 1024
    assert result == fake_vector

    call_args = hm.bedrock.invoke_model.call_args.kwargs
    body = json.loads(call_args["body"])
    assert body["inputText"] == "테스트 문서"
    assert body["dimensions"] == 1024


def test_existing_report_ids_scans_all(hm):
    mock_table = MagicMock()
    mock_table.scan.side_effect = [
        {"Items": [{"reportId": "daily-2026-06-20"}],
         "LastEvaluatedKey": {"x": 1}},
        {"Items": [{"reportId": "daily-2026-06-21"}]},
    ]
    hm.ddb.Table.return_value = mock_table

    result = hm.existing_report_ids()

    assert result == {"daily-2026-06-20", "daily-2026-06-21"}


def test_handler_skips_existing(hm):
    paginator = MagicMock()
    paginator.paginate.return_value = [{
        "Contents": [
            {"Key": "reports/daily/2026-06-20.md"},
            {"Key": "reports/daily/2026-06-21.md"},
        ]
    }]
    hm.s3.get_paginator.return_value = paginator

    mock_table = MagicMock()
    mock_table.scan.return_value = {
        "Items": [
            {"reportId": "daily-2026-06-20"},
            {"reportId": "daily-2026-06-21"},
        ]
    }
    hm.ddb.Table.return_value = mock_table

    result = hm.handler({}, None)

    assert result["totalReports"] == 2
    assert result["newlyEmbedded"] == 0
    assert result["skipped"] == 2


def test_handler_force_mode_reembeds(hm):
    paginator = MagicMock()
    paginator.paginate.return_value = [{
        "Contents": [{"Key": "reports/daily/2026-06-20.md"}]
    }]
    hm.s3.get_paginator.return_value = paginator

    mock_body = MagicMock()
    mock_body.read.return_value = b"# Test report"
    hm.s3.get_object.return_value = {"Body": mock_body}

    bedrock_body = MagicMock()
    bedrock_body.read.return_value = json.dumps({"embedding": [0.1] * 1024}).encode()
    hm.bedrock.invoke_model.return_value = {"body": bedrock_body}

    mock_table = MagicMock()
    mock_table.scan.return_value = {"Items": [{"reportId": "daily-2026-06-20"}]}
    hm.ddb.Table.return_value = mock_table

    result = hm.handler({"force": True}, None)

    assert result["totalReports"] == 1
    assert result["newlyEmbedded"] == 1
    mock_table.put_item.assert_called_once()
