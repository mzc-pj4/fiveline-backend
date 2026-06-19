import asyncio
from datetime import datetime, timedelta, timezone
from statistics import quantiles
from typing import Annotated

import boto3
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from app.deps import CurrentUser, require_admin

router = APIRouter(prefix="/api/admin/cicd", tags=["cicd"])

NAMESPACE = "fiveline"
REGION = "ap-northeast-2"
SERVICE_PORT_MAP = {
    "order-service": 8003,
    "product-service": 8002,
    "user-service": 8001,
}


def _load_k8s():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def _get_custom_api() -> client.CustomObjectsApi:
    _load_k8s()
    return client.CustomObjectsApi()


def _get_apps_api() -> client.AppsV1Api:
    _load_k8s()
    return client.AppsV1Api()


class RolloutActionRequest(BaseModel):
    service_name: str
    action: str  # "promote" | "abort"


@router.post("/rollout-action")
def rollout_action(
    _: Annotated[CurrentUser, Depends(require_admin)],
    body: RolloutActionRequest,
):
    try:
        if body.action == "promote":
            _get_custom_api().patch_namespaced_custom_object_status(
                group="argoproj.io",
                version="v1alpha1",
                namespace=NAMESPACE,
                plural="rollouts",
                name=body.service_name,
                body={"status": {"pauseConditions": None, "controllerPause": False}},
            )
        elif body.action == "abort":
            _get_custom_api().patch_namespaced_custom_object(
                group="argoproj.io",
                version="v1alpha1",
                namespace=NAMESPACE,
                plural="rollouts",
                name=body.service_name,
                body={"spec": {"abort": True}},
            )
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 액션: {body.action}")
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=e.reason)

    return {"status": "ok", "action": body.action, "service": body.service_name}


@router.get("/rollout-status")
def rollout_status(
    _: Annotated[CurrentUser, Depends(require_admin)],
    service: str = Query("order-service"),
):
    try:
        rollout = _get_custom_api().get_namespaced_custom_object(
            group="argoproj.io", version="v1alpha1",
            namespace=NAMESPACE, plural="rollouts",
            name=service,
        )
    except ApiException as e:
        if e.status == 404:
            return {"phase": "NotFound", "in_progress": False}
        raise HTTPException(status_code=e.status, detail=e.reason)

    spec = rollout.get("spec", {})
    status = rollout.get("status", {})

    steps = spec.get("strategy", {}).get("canary", {}).get("steps", [])
    current_step_index = status.get("currentStepIndex") or 0
    phase = status.get("phase", "Unknown")

    current_weight = 0
    for step in steps[:current_step_index]:
        if "setWeight" in step:
            current_weight = step["setWeight"]

    stable_hash = status.get("stableRS", "")
    canary_hash = status.get("currentPodHash", "")
    in_progress = bool(stable_hash and canary_hash and stable_hash != canary_hash)

    stable_image = ""
    canary_image = ""

    if in_progress:
        try:
            rs_list = _get_apps_api().list_namespaced_replica_set(
                namespace=NAMESPACE,
                label_selector=f"app={service}",
            )
            for rs in rs_list.items:
                pod_hash = (rs.metadata.labels or {}).get("rollouts-pod-template-hash", "")
                containers = (rs.spec.template.spec.containers or [])
                image = containers[0].image if containers else ""
                tag = image.split(":")[-1] if ":" in image else image
                if pod_hash == stable_hash:
                    stable_image = tag
                elif pod_hash == canary_hash:
                    canary_image = tag
        except Exception:
            pass

    return {
        "phase": phase,
        "in_progress": in_progress,
        "current_step_index": current_step_index,
        "steps_total": len(steps),
        "current_weight": current_weight,
        "paused": bool(status.get("pauseConditions")),
        "stable_image": stable_image,
        "canary_image": canary_image,
    }


@router.get("/realtime-metrics")
def realtime_metrics(
    _: Annotated[CurrentUser, Depends(require_admin)],
    service: str = Query("order-service"),
    minutes: int = Query(5, ge=1, le=60),
):
    try:
        elb = boto3.client("elbv2", region_name=REGION)
        cw = boto3.client("cloudwatch", region_name=REGION)

        albs = elb.describe_load_balancers()
        if not albs["LoadBalancers"]:
            raise HTTPException(status_code=503, detail="ALB를 찾을 수 없습니다")

        alb_arn = albs["LoadBalancers"][0]["LoadBalancerArn"]
        alb_suffix = "/".join(alb_arn.split("/")[-3:])
        dims = [{"Name": "LoadBalancer", "Value": alb_suffix}]

        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=minutes)
        period = minutes * 60

        def get_sum(metric_name: str) -> float:
            r = cw.get_metric_statistics(
                Namespace="AWS/ApplicationELB",
                MetricName=metric_name,
                Dimensions=dims,
                StartTime=start, EndTime=end,
                Period=period,
                Statistics=["Sum"],
            )
            return sum(p["Sum"] for p in r.get("Datapoints", []))

        def get_p99(metric_name: str) -> float:
            r = cw.get_metric_statistics(
                Namespace="AWS/ApplicationELB",
                MetricName=metric_name,
                Dimensions=dims,
                StartTime=start, EndTime=end,
                Period=period,
                ExtendedStatistics=["p99"],
            )
            points = r.get("Datapoints", [])
            if not points:
                return 0.0
            return points[0].get("ExtendedStatistics", {}).get("p99", 0.0)

        total = get_sum("RequestCount")
        error_5xx = get_sum("HTTPCode_Target_5XX_Count")
        error_4xx = get_sum("HTTPCode_Target_4XX_Count")
        p99_sec = get_p99("TargetResponseTime")

        return {
            "period_minutes": minutes,
            "total_requests": int(total),
            "error_rate": round(error_5xx / total * 100, 2) if total > 0 else 0.0,
            "error_4xx_rate": round(error_4xx / total * 100, 2) if total > 0 else 0.0,
            "p99_latency_ms": int(p99_sec * 1000),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/canary-probe")
async def canary_probe(
    _: Annotated[CurrentUser, Depends(require_admin)],
    service: str = Query("order-service"),
    count: int = Query(20, ge=5, le=50),
):
    port = SERVICE_PORT_MAP.get(service, 8003)
    url = f"http://{service}-canary.{NAMESPACE}.svc.cluster.local:{port}/api/health"

    latencies: list[float] = []
    errors = 0

    async with httpx.AsyncClient(timeout=5.0) as client:
        responses = await asyncio.gather(
            *[client.get(url) for _ in range(count)],
            return_exceptions=True,
        )

    for r in responses:
        if isinstance(r, Exception) or r.status_code >= 500:
            errors += 1
        else:
            latencies.append(r.elapsed.total_seconds() * 1000)

    p99 = int(quantiles(latencies, n=100)[98]) if len(latencies) >= 2 else (int(latencies[0]) if latencies else 0)
    avg = int(sum(latencies) / len(latencies)) if latencies else 0

    return {
        "service": service,
        "probe_count": count,
        "error_count": errors,
        "error_rate": round(errors / count * 100, 2),
        "p99_latency_ms": p99,
        "avg_latency_ms": avg,
        "canary_only": True,
    }
