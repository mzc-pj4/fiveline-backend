"""
Summary Writer Lambda
- Athena 로그/리소스 집계 + CloudWatch ALB 운영 메트릭 + 알람 카운트
- 실제 배포 DynamoDB 테이블 키: hash_key=service, range_key=date
- 결과를 dashboard_summary에 저장 → dashboard-builder가 읽어 data.json 생성
"""

import os
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

ATHENA_DB      = os.environ["ATHENA_DB"]
ATHENA_OUTPUT  = os.environ["ATHENA_OUTPUT"]
TABLE_NAME     = os.environ["TABLE_NAME"]
MONITORING_SVC = os.environ.get("MONITORING_SVC", "ecommerce")
ALB_LB         = os.environ.get("ALB_LB_NAME", "app/fiveline-alb/46f3ca3db6fcf6f3")

athena = boto3.client("athena")
ddb    = boto3.resource("dynamodb").Table(TABLE_NAME)
cw     = boto3.client("cloudwatch")


def D(v):
    if v is None or v == "":
        return Decimal("0")
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def run_athena(sql, timeout_sec=60):
    resp = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": ATHENA_DB},
        ResultConfiguration={"OutputLocation": ATHENA_OUTPUT},
    )
    qid = resp["QueryExecutionId"]
    for _ in range(timeout_sec):
        info = athena.get_query_execution(QueryExecutionId=qid)
        st = info["QueryExecution"]["Status"]["State"]
        if st == "SUCCEEDED":
            break
        if st in ("FAILED", "CANCELLED"):
            reason = info["QueryExecution"]["Status"].get("StateChangeReason", "")
            raise Exception(f"Athena {st}: {reason}")
        time.sleep(1)
    else:
        raise Exception(f"Athena timeout")

    rows = athena.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"]
    if not rows:
        return []
    headers = [c.get("VarCharValue", "") for c in rows[0]["Data"]]
    return [
        {headers[i]: c.get("VarCharValue", "") for i, c in enumerate(r["Data"])}
        for r in rows[1:]
    ]


def collect_log_stats():
    try:
        rows = run_athena(
            "SELECT SUM(total_events) AS total_events, "
            "SUM(error_count) AS total_errors, "
            "SUM(warning_count) AS total_warnings "
            "FROM events_hourly"
        )
        if not rows:
            return {"totalLogEvents": 0, "totalErrors": 0, "errorRate": Decimal("0")}
        r = rows[0]
        total  = int(r["total_events"] or 0)
        errors = int(r["total_errors"] or 0)
        rate   = round(100.0 * errors / total, 2) if total > 0 else 0
        return {
            "totalLogEvents": total,
            "totalErrors": errors,
            "totalWarnings": int(r["total_warnings"] or 0),
            "errorRate": D(rate),
        }
    except Exception as e:
        return {"totalLogEvents": 0, "totalErrors": 0, "totalWarnings": 0,
                "errorRate": Decimal("0"), "_logError": str(e)}


def collect_peak_hour():
    try:
        rows = run_athena(
            "SELECT year, month, day, hour, SUM(total_events) AS events "
            "FROM events_hourly "
            "GROUP BY year, month, day, hour "
            "ORDER BY events DESC LIMIT 1"
        )
        if not rows:
            return {"peakHour": "N/A", "peakHourEvents": 0}
        r = rows[0]
        label = f"{r['year']}-{r['month'].zfill(2)}-{r['day'].zfill(2)} {r['hour'].zfill(2)}:00"
        return {"peakHour": label, "peakHourEvents": int(r["events"])}
    except Exception:
        return {"peakHour": "N/A", "peakHourEvents": 0}


def collect_top_error_stream():
    try:
        rows = run_athena(
            "SELECT logstream, error_pct FROM events_hourly "
            "WHERE total_events >= 100 "
            "ORDER BY error_pct DESC LIMIT 1"
        )
        if not rows:
            return {"topErrorStream": "N/A", "topErrorPct": Decimal("0")}
        r = rows[0]
        return {"topErrorStream": r["logstream"], "topErrorPct": D(r["error_pct"] or 0)}
    except Exception:
        return {"topErrorStream": "N/A", "topErrorPct": Decimal("0")}


def collect_findings():
    try:
        by_check = run_athena(
            "SELECT checktype, SUM(finding_count) AS cnt "
            "FROM resource_findings_daily GROUP BY checktype"
        )
        by_resource = run_athena(
            "SELECT resourcetype, SUM(finding_count) AS cnt "
            "FROM resource_findings_daily GROUP BY resourcetype"
        )
        by_check_map    = {r["checktype"]:    int(r["cnt"]) for r in by_check}
        by_resource_map = {r["resourcetype"]: int(r["cnt"]) for r in by_resource}
        return {
            "totalFindings": sum(by_check_map.values()),
            "findingsByCheckType":    {k: D(v) for k, v in by_check_map.items()},
            "findingsByResourceType": {k: D(v) for k, v in by_resource_map.items()},
        }
    except Exception:
        return {"totalFindings": 0, "findingsByCheckType": {}, "findingsByResourceType": {}}


def collect_alb_metrics(today: str):
    """CloudWatch ALB 메트릭으로 당일 운영 지표 수집."""
    try:
        start = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end   = start + timedelta(days=1)
        resp  = cw.get_metric_data(
            MetricDataQueries=[
                {
                    "Id": "alb_req",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/ApplicationELB",
                            "MetricName": "RequestCount",
                            "Dimensions": [{"Name": "LoadBalancer", "Value": ALB_LB}],
                        },
                        "Period": 86400,
                        "Stat": "Sum",
                    },
                    "ReturnData": True,
                },
                {
                    "Id": "alb_5xx",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/ApplicationELB",
                            "MetricName": "HTTPCode_Target_5XX_Count",
                            "Dimensions": [{"Name": "LoadBalancer", "Value": ALB_LB}],
                        },
                        "Period": 86400,
                        "Stat": "Sum",
                    },
                    "ReturnData": True,
                },
                {
                    "Id": "alb_rt",
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/ApplicationELB",
                            "MetricName": "TargetResponseTime",
                            "Dimensions": [{"Name": "LoadBalancer", "Value": ALB_LB}],
                        },
                        "Period": 86400,
                        "Stat": "Average",
                    },
                    "ReturnData": True,
                },
            ],
            StartTime=start,
            EndTime=end,
        )
        results    = {r["Id"]: r["Values"] for r in resp["MetricDataResults"]}
        total_req  = int(sum(results.get("alb_req", [0])))
        total_5xx  = int(sum(results.get("alb_5xx", [0])))
        rt_vals    = results.get("alb_rt", [])
        avg_rt_ms  = round((sum(rt_vals) / len(rt_vals)) * 1000, 1) if rt_vals else 0
        failure_rt = round(100.0 * total_5xx / total_req, 2) if total_req > 0 else 0
        return {
            "totalOrders":        total_req,
            "failureRate":        D(failure_rt),
            "avgResponseTimeMs":  D(avg_rt_ms),
        }
    except Exception as e:
        return {
            "totalOrders": 0,
            "failureRate": Decimal("0"),
            "avgResponseTimeMs": Decimal("0"),
            "_cwError": str(e),
        }


def collect_alarm_count(today: str):
    """dashboard_summary 테이블에서 오늘 날짜 알람 카운트 합산."""
    try:
        resp  = ddb.scan(
            FilterExpression=Attr("date").eq(today),
            ProjectionExpression="totalCount",
        )
        return sum(int(item.get("totalCount", 0)) for item in resp.get("Items", []))
    except Exception:
        return 0


def handler(event, context):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now   = datetime.now(timezone.utc).isoformat()

    log_stats   = collect_log_stats()
    peak        = collect_peak_hour()
    top_error   = collect_top_error_stream()
    findings    = collect_findings()
    alb         = collect_alb_metrics(today)
    alarm_count = collect_alarm_count(today)

    item = {
        # 실제 배포 테이블 키 스키마: hash_key=service, range_key=date
        "service":   MONITORING_SVC,
        "date":      today,
        "updatedAt": now,
        # 어드민 대시보드 "오늘 운영 요약" 카드 (CloudWatch ALB)
        "totalOrders":       D(alb["totalOrders"]),
        "failureRate":       alb["failureRate"],
        "avgResponseTimeMs": alb["avgResponseTimeMs"],
        "currentAlarmCount": D(alarm_count),
        # 로그 분석 섹션 (Athena events_hourly)
        "totalLogEvents": D(log_stats["totalLogEvents"]),
        "totalErrors":    D(log_stats["totalErrors"]),
        "totalWarnings":  D(log_stats.get("totalWarnings", 0)),
        "errorRate":      log_stats["errorRate"],
        "peakHour":       peak["peakHour"],
        "peakHourEvents": D(peak["peakHourEvents"]),
        "topErrorStream": top_error["topErrorStream"],
        "topErrorPct":    top_error["topErrorPct"],
        # 리소스 점검 (Athena resource_findings_daily)
        "totalFindings":          D(findings["totalFindings"]),
        "findingsByCheckType":    findings["findingsByCheckType"],
        "findingsByResourceType": findings["findingsByResourceType"],
    }

    ddb.put_item(Item=item)

    return {
        "service":           MONITORING_SVC,
        "date":              today,
        "totalOrders":       alb["totalOrders"],
        "failureRate":       float(alb["failureRate"]),
        "avgResponseTimeMs": float(alb["avgResponseTimeMs"]),
        "currentAlarmCount": alarm_count,
        "totalLogEvents":    log_stats["totalLogEvents"],
        "errorRate":         float(log_stats["errorRate"]),
        "peakHour":          peak["peakHour"],
        "topErrorStream":    top_error["topErrorStream"],
        "totalFindings":     findings["totalFindings"],
    }
