import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import quantiles
from typing import Annotated

import boto3
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from app.deps import CurrentUser, require_admin

K8S_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
K8S_CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
K8S_API_HOST = "https://kubernetes.default.svc"


def _k8s_token() -> str:
    return Path(K8S_TOKEN_PATH).read_text().strip()


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
    if body.action == "promote":
        # Argo Rollouts 대시보드 API 서버 직접 호출 (가장 신뢰할 수 있는 방법)
        argo_api = "http://argo-rollouts.argo-rollouts.svc.cluster.local:3100"
        promote_url = f"{argo_api}/api/v1/namespaces/{NAMESPACE}/rollouts/{body.service_name}/promote"
        with httpx.Client(timeout=10.0) as http:
            resp = http.put(promote_url)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    elif body.action == "abort":
        try:
            _get_custom_api().patch_namespaced_custom_object(
                group="argoproj.io",
                version="v1alpha1",
                namespace=NAMESPACE,
                plural="rollouts",
                name=body.service_name,
                body={"spec": {"abort": True}},
            )
        except ApiException as e:
            raise HTTPException(status_code=e.status, detail=e.reason)

    else:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 액션: {body.action}")

    return {"status": "ok", "action": body.action, "service": body.service_name}


def _classify_step(step: dict, pause_conditions: list) -> dict:
    if "setWeight" in step:
        return {"type": "setWeight", "weight": step["setWeight"]}
    if "pause" in step:
        duration = step["pause"].get("duration") if step["pause"] else None
        if duration:
            return {"type": "pause_auto", "duration": str(duration)}
        return {"type": "pause_manual"}
    if "analysis" in step:
        return {"type": "analysis"}
    return {"type": "unknown"}


def _get_analysis_runs(service: str, canary_hash: str) -> list:
    try:
        label_selector = f"rollouts-pod-template-hash={canary_hash}" if canary_hash else None
        kwargs = dict(
            group="argoproj.io", version="v1alpha1",
            namespace=NAMESPACE, plural="analysisruns",
        )
        if label_selector:
            kwargs["label_selector"] = label_selector
        runs = _get_custom_api().list_namespaced_custom_object(**kwargs)
        result = []
        for r in runs.get("items", []):
            meta = r.get("metadata", {})
            status = r.get("status", {})
            metrics = status.get("metricResults", [])

            metric_details = []
            for m in metrics:
                measurements = m.get("measurements", [])
                values = []
                for meas in measurements:
                    raw = meas.get("value")
                    try:
                        values.append(round(float(raw), 2))
                    except (TypeError, ValueError):
                        pass
                metric_details.append({
                    "name": m.get("name", ""),
                    "phase": m.get("phase", "Unknown"),
                    "successful": m.get("successful", 0),
                    "failed": m.get("failed", 0),
                    "error": m.get("error", 0),
                    "latest_value": values[-1] if values else None,
                    "values": values,
                })

            successful = sum(m.get("successful", 0) for m in metrics)
            failed = sum(m.get("failed", 0) for m in metrics)
            error = sum(m.get("error", 0) for m in metrics)
            result.append({
                "name": meta.get("name", ""),
                "phase": status.get("phase", "Unknown"),
                "successful": successful,
                "failed": failed,
                "error": error,
                "started_at": meta.get("creationTimestamp"),
                "metric_details": metric_details,
            })
        result.sort(key=lambda x: x["started_at"] or "")
        return result
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"_get_analysis_runs failed: {e}")
        return []


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
    pause_conditions = status.get("pauseConditions") or []

    current_weight = 0
    for step in steps[:current_step_index]:
        if "setWeight" in step:
            current_weight = step["setWeight"]

    stable_hash = status.get("stableRS", "")
    canary_hash = status.get("currentPodHash", "")
    in_progress = bool(stable_hash and canary_hash and stable_hash != canary_hash)

    stable_image = ""
    canary_image = ""

    if in_progress or (phase == "Healthy" and stable_hash):
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

    steps_info = [_classify_step(s, pause_conditions) for s in steps]

    current_step_info = steps_info[current_step_index] if current_step_index < len(steps_info) else None
    is_manual_pause = (
        bool(pause_conditions)
        and current_step_info is not None
        and current_step_info.get("type") == "pause_manual"
    )

    analysis_runs = _get_analysis_runs(service, canary_hash) if in_progress else []

    return {
        "phase": phase,
        "in_progress": in_progress,
        "current_step_index": current_step_index,
        "steps_total": len(steps),
        "current_weight": current_weight,
        "paused": bool(pause_conditions),
        "is_manual_pause": is_manual_pause,
        "stable_image": stable_image,
        "canary_image": canary_image,
        "steps_info": steps_info,
        "current_step_info": current_step_info,
        "analysis_runs": analysis_runs,
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


PROMETHEUS_URL = "http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090"


@router.get("/pod-metrics")
async def pod_metrics(
    _: Annotated[CurrentUser, Depends(require_admin)],
    service: str = Query("order-service"),
):
    """Prometheus에서 Stable/Canary 파드 CPU·메모리 쿼리."""
    container = service

    async def query(promql: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": promql})
            r.raise_for_status()
            return r.json().get("data", {}).get("result", [])

    try:
        cpu_results = await query(
            f'rate(container_cpu_usage_seconds_total{{namespace="{NAMESPACE}",container="{container}"}}[1m])'
        )
        mem_results = await query(
            f'container_memory_working_set_bytes{{namespace="{NAMESPACE}",container="{container}"}}'
        )

        def parse_pods(results: list[dict], unit: float = 1.0) -> dict[str, float]:
            return {
                r["metric"].get("pod", ""): round(float(r["value"][1]) * unit, 4)
                for r in results if r.get("value")
            }

        cpu_by_pod = parse_pods(cpu_results, unit=100)   # → % cores
        mem_by_pod = parse_pods(mem_results, unit=1 / 1024 / 1024)  # → MiB

        pods = []
        for pod in set(list(cpu_by_pod) + list(mem_by_pod)):
            role = "canary" if "canary" in pod else "stable"
            pods.append({
                "pod": pod,
                "role": role,
                "cpu_percent": cpu_by_pod.get(pod),
                "memory_mib": mem_by_pod.get(pod),
            })

        pods.sort(key=lambda p: (p["role"], p["pod"]))
        return {"service": service, "pods": pods}

    except Exception as e:
        return {"service": service, "pods": [], "error": str(e)}
