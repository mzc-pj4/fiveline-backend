import os
from typing import Annotated

import boto3
from fastapi import APIRouter, Depends
from boto3.dynamodb.conditions import Key

from app.deps import CurrentUser, require_admin

router = APIRouter(prefix="/api/admin/aiops", tags=["aiops"])

REGION = "ap-northeast-2"
TABLE_NAME = os.getenv("AIOPS_TABLE", "fiveline-dev-aiops-canary-logs")


def _get_table():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    return dynamodb.Table(TABLE_NAME)


@router.get("/deployments")
def list_deployments(
    _: Annotated[CurrentUser, Depends(require_admin)],
    service: str = "order-service",
    limit: int = 10,
):
    table = _get_table()
    resp = table.query(
        KeyConditionExpression=Key("service_name").eq(service),
        ScanIndexForward=False,
        Limit=limit,
    )
    items = []
    for item in resp.get("Items", []):
        items.append({
            "service_name": item.get("service_name"),
            "deployed_at": item.get("deployed_at"),
            "image_tag": item.get("image_tag"),
            "total_requests": int(item.get("total_requests", 0)),
            "error_count": int(item.get("error_count", 0)),
            "error_rate": float(item.get("error_rate", 0)),
            "error_4xx_count": int(item.get("error_4xx_count", 0)),
            "error_4xx_rate": float(item.get("error_4xx_rate", 0)),
            "p99_latency_ms": int(item.get("p99_latency_ms", 0)),
            "risk_level": item.get("risk_level", ""),
            "risk_reason": item.get("risk_reason", ""),
            "trivy_critical": int(item.get("trivy_critical", 0)),
            "trivy_high": int(item.get("trivy_high", 0)),
            "trivy_medium": int(item.get("trivy_medium", 0)),
            "trivy_low": int(item.get("trivy_low", 0)),
            "ai_status": item.get("ai_status"),
            "ai_recommendation": item.get("ai_recommendation"),
            "ai_reason": item.get("ai_reason"),
            "step_index": int(item["step_index"]) if item.get("step_index") else None,
            "canary_weight": int(item["canary_weight"]) if item.get("canary_weight") else None,
            "sonar_coverage": float(item["sonar_coverage"]) if item.get("sonar_coverage") is not None else None,
            "sonar_bugs": int(item["sonar_bugs"]) if item.get("sonar_bugs") is not None else None,
            "sonar_vulnerabilities": int(item["sonar_vulnerabilities"]) if item.get("sonar_vulnerabilities") is not None else None,
            "sonar_code_smells": int(item["sonar_code_smells"]) if item.get("sonar_code_smells") is not None else None,
            "sonar_quality_gate": item.get("sonar_quality_gate"),
        })
    return {"items": items, "total": len(items)}
