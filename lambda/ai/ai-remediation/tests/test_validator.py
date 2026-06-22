"""
validator.py 테스트
- whitelist + 위험 패턴 + Owner 태그 검증 로직 검사
"""
import sys
from pathlib import Path
from unittest.mock import patch

# 상위 폴더 import 가능하게
sys.path.insert(0, str(Path(__file__).parent.parent))

from validator import validate_request, _get_tag


# ─────────────────────────────────────────────────────────────────────────────
# Action whitelist 테스트
# ─────────────────────────────────────────────────────────────────────────────

@patch("validator._validate_aws_resource")
def test_delete_action_allowed(mock_validate):
    """delete 액션은 허용"""
    mock_validate.return_value = {"exists": True, "owned_by_us": True}
    result = validate_request("vol-abc123", "delete")
    assert result["allowed"] is True


@patch("validator._validate_aws_resource")
def test_tag_action_allowed(mock_validate):
    """tag 액션은 허용"""
    mock_validate.return_value = {"exists": True, "owned_by_us": True}
    result = validate_request("vol-abc123", "tag")
    assert result["allowed"] is True


@patch("validator._validate_aws_resource")
def test_modify_action_allowed(mock_validate):
    """modify 액션은 허용"""
    mock_validate.return_value = {"exists": True, "owned_by_us": True}
    result = validate_request("vol-abc123", "modify")
    assert result["allowed"] is True


def test_unknown_action_blocked():
    """모르는 액션은 차단"""
    result = validate_request("vol-abc123", "scale_up")
    assert result["allowed"] is False
    assert "허용되지 않은 액션" in result["reason"]


def test_destroy_action_blocked():
    """destroy 같은 위험 액션은 차단 (whitelist에 없음)"""
    result = validate_request("vol-abc123", "destroy")
    assert result["allowed"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 위험 자원 패턴 차단
# ─────────────────────────────────────────────────────────────────────────────

def test_prod_pattern_blocked():
    """*-prod-* 패턴은 차단"""
    result = validate_request("vol-prod-abc123", "delete")
    assert result["allowed"] is False
    assert "위험 자원 패턴" in result["reason"]


def test_i_prod_blocked():
    """i-prod* 인스턴스 ID는 차단"""
    result = validate_request("i-prod123abcdef", "delete")
    assert result["allowed"] is False


def test_rds_prod_blocked():
    """rds-prod-* 는 차단"""
    result = validate_request("rds-prod-customer-db", "delete")
    assert result["allowed"] is False


def test_production_pattern_blocked():
    """*-production-* 도 차단"""
    result = validate_request("vol-production-abc", "delete")
    assert result["allowed"] is False


# ─────────────────────────────────────────────────────────────────────────────
# AWS 자원 존재 + Owner 태그 검증
# ─────────────────────────────────────────────────────────────────────────────

@patch("validator._validate_aws_resource")
def test_non_existing_resource_blocked(mock_validate):
    """존재하지 않는 자원은 차단 (환각 ID 차단)"""
    mock_validate.return_value = {"exists": False}
    result = validate_request("vol-doesnotexist", "delete")
    assert result["allowed"] is False
    assert "자원 미존재" in result["reason"]


@patch("validator._validate_aws_resource")
def test_other_team_resource_blocked(mock_validate):
    """다른 팀원 자원 (Owner != jihoo) 은 차단"""
    mock_validate.return_value = {
        "exists": True,
        "owner": "other_team_member",
        "owned_by_us": False,
    }
    result = validate_request("vol-other-team", "delete")
    assert result["allowed"] is False
    assert "다른 팀원 자원" in result["reason"]


@patch("validator._validate_aws_resource")
def test_no_owner_tag_allowed(mock_validate):
    """Owner 태그 없는 자원은 허용 (Resource Checker가 발견한 거)"""
    mock_validate.return_value = {
        "exists": True,
        "owner": None,
        "owned_by_us": True,
    }
    result = validate_request("vol-no-tag", "delete")
    assert result["allowed"] is True


@patch("validator._validate_aws_resource")
def test_jihoo_owned_allowed(mock_validate):
    """Owner=jihoo 자원은 허용"""
    mock_validate.return_value = {
        "exists": True,
        "owner": "jihoo",
        "owned_by_us": True,
    }
    result = validate_request("vol-mine", "delete")
    assert result["allowed"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────────────────────────────────────

def test_get_tag_existing():
    """태그 리스트에서 존재하는 키 찾기"""
    tags = [
        {"Key": "Name", "Value": "test"},
        {"Key": "Owner", "Value": "jihoo"},
    ]
    assert _get_tag(tags, "Owner") == "jihoo"


def test_get_tag_missing():
    """없는 키는 None 반환"""
    tags = [{"Key": "Name", "Value": "test"}]
    assert _get_tag(tags, "Owner") is None


def test_get_tag_empty_list():
    """빈 리스트는 None 반환"""
    assert _get_tag([], "Owner") is None
