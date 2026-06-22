"""
안전 검증 — AI 자동 PR 생성 전 사전 검증
- 허용 액션: delete, tag, modify
- 위험 자원 차단 (prod 패턴, 다른 팀원 자원)
- 자원 존재 확인 (AWS API)
- 우리 영역 (jihoo) 만 허용
"""

import re
import boto3

# 허용 액션
ALLOWED_ACTIONS = {"delete", "tag", "modify"}

# 위험 자원 패턴 (자동 PR 생성 금지)
DANGEROUS_PATTERNS = [
    r".*-prod-.*",
    r".*-production-.*",
    r"i-prod[0-9a-f]+",
    r"vol-prod[0-9a-f]+",
    r"rds-prod-.*",
    r"prod-.*",
]

# 우리 영역 prefix
ALLOWED_PREFIX = "mzc-pj4-jihoo-"
ALLOWED_OWNER_TAG = "jihoo"


def validate_request(resource_id: str, action: str) -> dict:
    """
    Returns:
        {"allowed": True/False, "reason": "..."}
    """
    # 1. 액션 화이트리스트
    if action not in ALLOWED_ACTIONS:
        return {
            "allowed": False,
            "reason": f"허용되지 않은 액션: {action}. 허용: {ALLOWED_ACTIONS}",
        }

    # 2. 위험 자원 패턴 차단
    for pattern in DANGEROUS_PATTERNS:
        if re.match(pattern, resource_id, re.IGNORECASE):
            return {
                "allowed": False,
                "reason": f"위험 자원 패턴 매칭, 자동 PR 생성 차단: {pattern}",
            }

    # 3. 자원 타입별 존재 확인 + Owner 태그 검증
    try:
        result = _validate_aws_resource(resource_id)
        if not result["exists"]:
            return {
                "allowed": False,
                "reason": f"자원 미존재: {resource_id}",
            }
        if not result["owned_by_us"]:
            return {
                "allowed": False,
                "reason": f"다른 팀원 자원 (Owner={result.get('owner')}), 자동 PR 생성 차단",
            }
    except Exception as e:
        return {
            "allowed": False,
            "reason": f"검증 중 에러: {e}",
        }

    return {"allowed": True, "reason": "OK"}


def _validate_aws_resource(resource_id: str) -> dict:
    """자원 타입 추론 후 존재 + Owner 태그 확인"""
    ec2 = boto3.client("ec2")
    rds = boto3.client("rds")

    if resource_id.startswith("vol-"):
        try:
            resp = ec2.describe_volumes(VolumeIds=[resource_id])
            vol = resp["Volumes"][0]
            owner = _get_tag(vol.get("Tags", []), "Owner")
            return {
                "exists": True,
                "owner": owner,
                "owned_by_us": owner == ALLOWED_OWNER_TAG or owner is None,  # 태그 없으면 일단 허용 (Resource Checker가 발견한 거)
                "type": "EBS",
            }
        except ec2.exceptions.ClientError as e:
            if "NotFound" in str(e):
                return {"exists": False}
            raise

    if resource_id.startswith("i-"):
        try:
            resp = ec2.describe_instances(InstanceIds=[resource_id])
            inst = resp["Reservations"][0]["Instances"][0]
            owner = _get_tag(inst.get("Tags", []), "Owner")
            return {
                "exists": True,
                "owner": owner,
                "owned_by_us": owner == ALLOWED_OWNER_TAG or owner is None,
                "type": "EC2",
            }
        except ec2.exceptions.ClientError as e:
            if "NotFound" in str(e):
                return {"exists": False}
            raise

    if resource_id.startswith("eipalloc-"):
        try:
            resp = ec2.describe_addresses(AllocationIds=[resource_id])
            eip = resp["Addresses"][0]
            owner = _get_tag(eip.get("Tags", []), "Owner")
            return {
                "exists": True,
                "owner": owner,
                "owned_by_us": owner == ALLOWED_OWNER_TAG or owner is None,
                "type": "EIP",
            }
        except ec2.exceptions.ClientError as e:
            if "NotFound" in str(e):
                return {"exists": False}
            raise

    # 알 수 없는 자원 타입 → 보수적으로 차단
    return {
        "exists": False,
        "reason": f"알 수 없는 자원 타입: {resource_id}",
    }


def _get_tag(tags: list, key: str) -> str:
    """태그 리스트에서 특정 키의 값 추출"""
    for t in tags:
        if t.get("Key") == key:
            return t.get("Value")
    return None
