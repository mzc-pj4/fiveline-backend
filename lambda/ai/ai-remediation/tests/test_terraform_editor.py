"""
terraform_editor.py 테스트 — Bedrock Claude 응답 파싱
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from terraform_editor import generate_terraform_change


def _make_mock_bedrock(response_text: str):
    """Bedrock converse() 응답을 mock"""
    mock = MagicMock()
    mock.converse.return_value = {
        "output": {"message": {"content": [{"text": response_text}]}}
    }
    return mock


def test_normal_json_response():
    """정상 JSON 응답 파싱"""
    response = json.dumps({
        "files_changed": [
            {"filename": "data_pipeline.tf", "new_content": "# updated\n"}
        ],
        "impact_analysis": "EBS vol-abc 삭제. 의존성 없음.",
        "risk_level": "low",
    })
    bedrock = _make_mock_bedrock(response)

    result = generate_terraform_change(
        bedrock_client=bedrock,
        model_id="claude-3-5-sonnet",
        resource_id="vol-abc123",
        action="delete",
        rationale="unattached",
        tf_files={"data_pipeline.tf": 'resource "aws_ebs_volume" "vol-abc123" {}'},
    )

    assert result["risk_level"] == "low"
    assert len(result["files_changed"]) == 1
    assert result["files_changed"][0]["filename"] == "data_pipeline.tf"


def test_json_wrapped_in_code_block():
    """```json ... ``` 코드 블록으로 감싼 응답도 파싱"""
    inner = json.dumps({
        "files_changed": [{"filename": "test.tf", "new_content": "ok"}],
        "impact_analysis": "ok",
        "risk_level": "medium",
    })
    response = f"여기 결과입니다:\n```json\n{inner}\n```\n끝"
    bedrock = _make_mock_bedrock(response)

    result = generate_terraform_change(
        bedrock_client=bedrock,
        model_id="claude-3-5-sonnet",
        resource_id="vol-abc",
        action="delete",
        rationale="",
        tf_files={"test.tf": ""},
    )

    assert result["risk_level"] == "medium"


def test_invalid_json_raises():
    """파싱 불가 응답은 에러"""
    bedrock = _make_mock_bedrock("이건 JSON 아니에요")

    with pytest.raises(RuntimeError, match="JSON 파싱 실패"):
        generate_terraform_change(
            bedrock_client=bedrock,
            model_id="claude-3-5-sonnet",
            resource_id="vol-abc",
            action="delete",
            rationale="",
            tf_files={"test.tf": ""},
        )


def test_missing_files_changed_raises():
    """files_changed 키 누락 시 에러"""
    response = json.dumps({"impact_analysis": "x", "risk_level": "low"})
    bedrock = _make_mock_bedrock(response)

    with pytest.raises(RuntimeError, match="files_changed 누락"):
        generate_terraform_change(
            bedrock_client=bedrock,
            model_id="claude-3-5-sonnet",
            resource_id="vol-abc",
            action="delete",
            rationale="",
            tf_files={"test.tf": ""},
        )


def test_empty_files_changed_raises():
    """변경 파일 0개면 에러 (AI가 자원 못 찾은 경우)"""
    response = json.dumps({
        "files_changed": [],
        "impact_analysis": "찾을 수 없음",
        "risk_level": "low",
    })
    bedrock = _make_mock_bedrock(response)

    with pytest.raises(RuntimeError, match="변경 파일이 없음"):
        generate_terraform_change(
            bedrock_client=bedrock,
            model_id="claude-3-5-sonnet",
            resource_id="vol-abc",
            action="delete",
            rationale="",
            tf_files={"test.tf": ""},
        )


def test_default_risk_level_when_missing():
    """risk_level 누락 시 medium 기본값"""
    response = json.dumps({
        "files_changed": [{"filename": "t.tf", "new_content": ""}],
    })
    bedrock = _make_mock_bedrock(response)

    result = generate_terraform_change(
        bedrock_client=bedrock,
        model_id="claude-3-5-sonnet",
        resource_id="vol-abc",
        action="delete",
        rationale="",
        tf_files={"t.tf": ""},
    )

    assert result["risk_level"] == "medium"
    assert "impact_analysis" in result


def test_prompt_includes_resource_id():
    """프롬프트에 자원 ID + 액션 포함 검증 (Bedrock 호출 인자 검사)"""
    bedrock = _make_mock_bedrock(json.dumps({
        "files_changed": [{"filename": "t.tf", "new_content": ""}],
        "impact_analysis": "x",
        "risk_level": "low",
    }))

    generate_terraform_change(
        bedrock_client=bedrock,
        model_id="claude-3-5-sonnet",
        resource_id="vol-MAGIC123",
        action="delete",
        rationale="my reason",
        tf_files={"t.tf": ""},
    )

    # Bedrock 호출 시 프롬프트에 자원 ID·액션·사유 다 포함됐는지 확인
    call_args = bedrock.converse.call_args.kwargs
    prompt_text = call_args["messages"][0]["content"][0]["text"]
    assert "vol-MAGIC123" in prompt_text
    assert "delete" in prompt_text
    assert "my reason" in prompt_text
