"""
AI Auto-Remediation Lambda
- 사용자가 챗봇에 자연어 요청 → LangGraph가 이 Lambda 호출
- 입력: {"resource_id": "vol-xxx", "action": "delete", "rationale": "..."}
- 출력: {"pr_url": "https://...", "risk_level": "low", ...}

내부 흐름:
1. 안전 검증 (validator)
2. 현재 Terraform 코드 읽기 (github_client)
3. Bedrock Claude로 변경 코드 생성
4. 새 브랜치 + commit + PR 자동 생성 (github_client)
5. Audit DDB 기록
"""

import json
import os
from datetime import datetime, timezone

import boto3

from validator import validate_request
from github_client import GitHubClient
from terraform_editor import generate_terraform_change

# 환경변수
GITHUB_TOKEN_SECRET = os.environ["GITHUB_TOKEN_SECRET"]  # Secrets Manager ARN
GITHUB_REPO = os.environ.get("GITHUB_REPO", "Kjihoo/aws-aiops-platform")  # owner/repo
GITHUB_BASE_BRANCH = os.environ.get("GITHUB_BASE_BRANCH", "feat/jihoo-data-pipeline")
TERRAFORM_PATH_PREFIX = os.environ.get("TERRAFORM_PATH_PREFIX", "terraform/jihoo")
AUDIT_TABLE = os.environ["AUDIT_TABLE"]
BEDROCK_MODEL = os.environ.get("BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")
MOCK_MODE = os.environ.get("MOCK_MODE", "false").lower() == "true"  # 테스트용

# AWS 클라이언트
secretsmanager = boto3.client("secretsmanager")
bedrock = boto3.client("bedrock-runtime")
ddb = boto3.resource("dynamodb")


def get_github_token():
    """Secrets Manager 에서 GitHub PAT 가져오기"""
    resp = secretsmanager.get_secret_value(SecretId=GITHUB_TOKEN_SECRET)
    return resp["SecretString"]


def log_audit(session_id, request, result):
    """모든 Remediation 액션을 DDB 에 기록 (감사 추적)"""
    ddb.Table(AUDIT_TABLE).put_item(Item={
        "request_id": result.get("request_id", f"req-{int(datetime.now().timestamp())}"),
        "session_id": session_id,
        "resource_id": request.get("resource_id"),
        "action": request.get("action"),
        "rationale": request.get("rationale", ""),
        "status": result.get("status"),
        "pr_url": result.get("pr_url", ""),
        "risk_level": result.get("risk_level", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mock_mode": MOCK_MODE,
    })


def handler(event, context):
    """
    호출 형식:
    {
        "resource_id": "vol-01e455b067179d5bf",
        "action": "delete",          # delete | tag | modify
        "rationale": "6/2 이후 unattached, snapshot 없음",
        "session_id": "abc-123"      # LangGraph 세션 ID (감사용)
    }
    """
    resource_id = event.get("resource_id", "")
    action = event.get("action", "")
    rationale = event.get("rationale", "")
    session_id = event.get("session_id", "unknown")

    if not resource_id or not action:
        return {
            "status": "error",
            "error": "resource_id 와 action 필수",
        }

    request_id = f"req-{int(datetime.now().timestamp())}-{resource_id[:8]}"
    result = {"request_id": request_id, "status": "pending"}

    try:
        # 1. 안전 검증
        validation = validate_request(resource_id, action)
        if not validation["allowed"]:
            result.update({
                "status": "rejected",
                "reason": validation["reason"],
            })
            log_audit(session_id, event, result)
            return result

        # 2. GitHub 클라이언트 초기화
        token = get_github_token()
        gh = GitHubClient(token=token, repo=GITHUB_REPO)

        # 3. 현재 Terraform 코드 읽기
        tf_files = gh.fetch_terraform_files(
            base_branch=GITHUB_BASE_BRANCH,
            path_prefix=TERRAFORM_PATH_PREFIX,
        )

        # 4. Bedrock Claude 로 변경 코드 생성
        change = generate_terraform_change(
            bedrock_client=bedrock,
            model_id=BEDROCK_MODEL,
            resource_id=resource_id,
            action=action,
            rationale=rationale,
            tf_files=tf_files,
        )

        # 5. PR 생성 (MOCK 모드면 실제 호출 X)
        if MOCK_MODE:
            pr_url = f"[MOCK] would create PR for {resource_id} ({action})"
            print(f"[MOCK MODE] PR not actually created. Change: {json.dumps(change, ensure_ascii=False)[:500]}")
        else:
            pr_url = gh.create_remediation_pr(
                base_branch=GITHUB_BASE_BRANCH,
                request_id=request_id,
                resource_id=resource_id,
                action=action,
                change=change,
                session_id=session_id,
            )

        result.update({
            "status": "pr_created" if not MOCK_MODE else "mock_pr",
            "pr_url": pr_url,
            "risk_level": change.get("risk_level", "unknown"),
            "impact_analysis": change.get("impact_analysis", ""),
            "files_changed": [f["filename"] for f in change.get("files_changed", [])],
        })

    except Exception as e:
        result.update({
            "status": "error",
            "error": str(e),
            "errorType": type(e).__name__,
        })

    finally:
        log_audit(session_id, event, result)

    return result
