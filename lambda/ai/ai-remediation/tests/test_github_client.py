"""
github_client.py 테스트 — GitHub API 호출 (mock urllib)
"""
import base64
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from github_client import GitHubClient


def _make_mock_response(data: dict, raw_text: str = None):
    """urllib.urlopen() 응답을 mock"""
    mock_resp = MagicMock()
    if raw_text is not None:
        mock_resp.read.return_value = raw_text.encode("utf-8")
    else:
        mock_resp.read.return_value = json.dumps(data).encode("utf-8")
    mock_resp.__enter__ = lambda self: mock_resp
    mock_resp.__exit__ = lambda *a: None
    return mock_resp


def test_client_initialization():
    """클라이언트 초기화 시 헤더 설정"""
    gh = GitHubClient(token="ghp_test", repo="owner/repo")
    assert gh.repo == "owner/repo"
    assert "token ghp_test" in gh.headers["Authorization"]
    assert "github+json" in gh.headers["Accept"]


@patch("github_client.request.urlopen")
def test_get_branch_sha(mock_urlopen):
    """브랜치 SHA 조회"""
    mock_urlopen.return_value = _make_mock_response({
        "object": {"sha": "abc123def"}
    })

    gh = GitHubClient(token="ghp_test", repo="owner/repo")
    sha = gh.get_branch_sha("develop")

    assert sha == "abc123def"


@patch("github_client.request.urlopen")
def test_create_branch(mock_urlopen):
    """새 브랜치 생성 호출"""
    mock_urlopen.return_value = _make_mock_response({"ref": "refs/heads/new-branch"})

    gh = GitHubClient(token="ghp_test", repo="owner/repo")
    gh.create_branch("new-branch", "base_sha_123")

    # POST 요청 + body 검증
    call_args = mock_urlopen.call_args[0][0]
    body = json.loads(call_args.data.decode("utf-8"))
    assert body["ref"] == "refs/heads/new-branch"
    assert body["sha"] == "base_sha_123"


@patch("github_client.request.urlopen")
def test_open_pr_returns_url(mock_urlopen):
    """PR 생성 후 URL 반환"""
    mock_urlopen.return_value = _make_mock_response({
        "html_url": "https://github.com/owner/repo/pull/42",
        "number": 42,
    })

    gh = GitHubClient(token="ghp_test", repo="owner/repo")
    url = gh.open_pr(
        title="Test PR",
        head="feat/test",
        base="develop",
        body="test body",
    )

    assert url == "https://github.com/owner/repo/pull/42"


@patch("github_client.request.urlopen")
def test_fetch_terraform_files_filters_tf(mock_urlopen):
    """디렉터리 listing 중 .tf 파일만 가져옴"""
    listing_response = _make_mock_response([
        {"type": "file", "name": "main.tf",
         "download_url": "https://raw.example.com/main.tf"},
        {"type": "file", "name": "README.md",
         "download_url": "https://raw.example.com/README.md"},
        {"type": "file", "name": "outputs.tf",
         "download_url": "https://raw.example.com/outputs.tf"},
        {"type": "dir", "name": "subfolder"},
    ])
    raw_main = _make_mock_response({}, raw_text="# main.tf content")
    raw_outputs = _make_mock_response({}, raw_text="# outputs.tf content")

    # 호출 순서: listing → main.tf raw → outputs.tf raw
    mock_urlopen.side_effect = [listing_response, raw_main, raw_outputs]

    gh = GitHubClient(token="ghp_test", repo="owner/repo")
    files = gh.fetch_terraform_files("develop", "terraform/jihoo")

    assert "main.tf" in files
    assert "outputs.tf" in files
    assert "README.md" not in files
    assert "subfolder" not in files
    assert files["main.tf"] == "# main.tf content"


@patch("github_client.request.urlopen")
def test_pr_body_includes_warning(mock_urlopen):
    """PR 본문에 AI 자동 생성 경고 포함"""
    mock_urlopen.return_value = _make_mock_response({
        "html_url": "https://github.com/x/y/pull/1"
    })

    gh = GitHubClient(token="ghp_test", repo="owner/repo")
    change = {
        "files_changed": [{"filename": "test.tf"}],
        "impact_analysis": "no impact",
        "risk_level": "low",
    }
    body = gh._build_pr_body(
        request_id="req-1",
        resource_id="vol-abc",
        action="delete",
        change=change,
        session_id="session-1",
    )

    assert "AI 자동 생성" in body
    assert "검토 부탁드립니다" in body
    assert "vol-abc" in body
    assert "delete" in body
    assert "LOW" in body


@patch("github_client.request.urlopen")
def test_add_labels_swallows_errors(mock_urlopen):
    """라벨 추가 실패해도 예외 안 던짐 (선택적 기능)"""
    from urllib.error import HTTPError
    mock_urlopen.side_effect = HTTPError("url", 404, "Not Found", {}, None)

    gh = GitHubClient(token="ghp_test", repo="owner/repo")
    # 예외 안 나야 함
    gh.add_labels(42, ["ai-generated"])
