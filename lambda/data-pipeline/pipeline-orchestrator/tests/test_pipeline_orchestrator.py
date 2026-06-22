"""
pipeline-orchestrator/handler.py 테스트
- Glue Job 호출 → 대기 → Athena MSCK REPAIR → Lambda 체인
"""
import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("GLUE_JOB_NAME", "test-glue-job")
os.environ.setdefault("SUMMARY_WRITER_NAME", "test-summary-writer")
os.environ.setdefault("DASHBOARD_BUILDER_NAME", "test-dashboard-builder")
os.environ.setdefault("ATHENA_DB", "test_db")
os.environ.setdefault("ATHENA_OUTPUT", "s3://test/output/")


@pytest.fixture
def hm():
    """handler.py 를 unique 이름으로 로드"""
    spec = importlib.util.spec_from_file_location(
        "orchestrator_handler",
        Path(__file__).parent.parent / "handler.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orchestrator_handler"] = mod
    spec.loader.exec_module(mod)
    mod.glue = MagicMock()
    mod.athena = MagicMock()
    mod.lambda_ = MagicMock()
    yield mod
    sys.modules.pop("orchestrator_handler", None)


# ─────────────────────────────────────────────────────────────────────────────
# Glue Job 대기
# ─────────────────────────────────────────────────────────────────────────────

def test_wait_glue_succeeded_on_first_poll(hm):
    """첫 poll에서 SUCCEEDED 면 즉시 반환"""
    hm.glue.get_job_run.return_value = {
        "JobRun": {"JobRunState": "SUCCEEDED"}
    }

    state = hm.wait_glue("run-1", max_polls=10)
    assert state == "SUCCEEDED"
    assert hm.glue.get_job_run.call_count == 1


def test_wait_glue_eventually_succeeds(hm):
    """RUNNING → RUNNING → SUCCEEDED 흐름"""
    hm.glue.get_job_run.side_effect = [
        {"JobRun": {"JobRunState": "RUNNING"}},
        {"JobRun": {"JobRunState": "RUNNING"}},
        {"JobRun": {"JobRunState": "SUCCEEDED"}},
    ]

    with patch.object(hm, "time", MagicMock()):
        state = hm.wait_glue("run-2", max_polls=10)

    assert state == "SUCCEEDED"
    assert hm.glue.get_job_run.call_count == 3


def test_wait_glue_failed_state(hm):
    """FAILED 상태는 즉시 반환"""
    hm.glue.get_job_run.return_value = {
        "JobRun": {"JobRunState": "FAILED", "ErrorMessage": "boom"}
    }

    state = hm.wait_glue("run-3", max_polls=10)
    assert state == "FAILED"


# ─────────────────────────────────────────────────────────────────────────────
# Athena MSCK REPAIR
# ─────────────────────────────────────────────────────────────────────────────

def test_msck_repair_runs_query(hm):
    """MSCK REPAIR TABLE 쿼리 실행"""
    hm.athena.start_query_execution.return_value = {
        "QueryExecutionId": "qid-1"
    }
    hm.athena.get_query_execution.return_value = {
        "QueryExecution": {"Status": {"State": "SUCCEEDED"}}
    }

    with patch.object(hm, "time", MagicMock()):
        hm.msck_repair("service_events")

    call_args = hm.athena.start_query_execution.call_args.kwargs
    assert "MSCK REPAIR TABLE service_events" in call_args["QueryString"]
    assert call_args["QueryExecutionContext"]["Database"] == "test_db"


# ─────────────────────────────────────────────────────────────────────────────
# Lambda 체인 호출
# ─────────────────────────────────────────────────────────────────────────────

def test_invoke_lambda_calls_aws_lambda(hm):
    """체인 Lambda 가 invoke 호출됨"""
    hm.invoke_lambda("test-summary-writer")

    call_args = hm.lambda_.invoke.call_args.kwargs
    assert call_args["FunctionName"] == "test-summary-writer"
    # InvocationType 은 핸들러 구현 디테일 — Event 또는 RequestResponse 둘 다 OK
    assert call_args["InvocationType"] in ("Event", "RequestResponse")


# ─────────────────────────────────────────────────────────────────────────────
# 전체 흐름
# ─────────────────────────────────────────────────────────────────────────────

def test_handler_runs_full_chain(hm):
    """Glue → MSCK → Summary Writer → Dashboard Builder 순서"""
    hm.glue.start_job_run.return_value = {"JobRunId": "run-x"}
    hm.glue.get_job_run.return_value = {
        "JobRun": {"JobRunState": "SUCCEEDED"}
    }
    hm.athena.start_query_execution.return_value = {"QueryExecutionId": "qid-x"}
    hm.athena.get_query_execution.return_value = {
        "QueryExecution": {"Status": {"State": "SUCCEEDED"}}
    }

    with patch.object(hm, "time", MagicMock()):
        hm.handler({}, None)

    hm.glue.start_job_run.assert_called()
    assert hm.athena.start_query_execution.call_count >= 1

    invoked_names = [
        c.kwargs["FunctionName"]
        for c in hm.lambda_.invoke.call_args_list
    ]
    assert "test-summary-writer" in invoked_names
    assert "test-dashboard-builder" in invoked_names
