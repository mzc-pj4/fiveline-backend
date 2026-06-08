import json
import os
import time
from datetime import datetime, timezone

import boto3

DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
S3_BUCKET      = os.environ["S3_BUCKET"]
S3_PREFIX      = os.environ.get("S3_PREFIX", "raw/cost-estimation/")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
COST_THRESHOLD = float(os.environ.get("COST_THRESHOLD", "100.0"))
REGION         = os.environ.get("AWS_REGION", "ap-northeast-2")

# Athena 설정 — 테이블명은 jihoo와 확인 후 수정
ATHENA_DB      = os.environ.get("ATHENA_DB",    "mzc_pj4_jihoo_data_lake_dev")
ATHENA_TABLE   = os.environ.get("ATHENA_TABLE", "cw_metrics")        # TODO: jihoo 확인 후 수정
ATHENA_RESULTS = os.environ.get("ATHENA_RESULTS", "s3://mzc-pj4-jihoo-data-lake-dev/athena-results/")

REGION_LOCATION = {
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "us-east-1":      "US East (N. Virginia)",
    "us-west-2":      "US West (Oregon)",
}

ec2_client     = boto3.client("ec2",      region_name=REGION)
rds_client     = boto3.client("rds",      region_name=REGION)
athena_client  = boto3.client("athena",   region_name=REGION)
pricing_client = boto3.client("pricing",  region_name="us-east-1")  # Pricing API는 us-east-1 고정
dynamodb       = boto3.resource("dynamodb", region_name=REGION)
s3             = boto3.client("s3",       region_name=REGION)

HOURS_PER_MONTH = 720


def lambda_handler(event, context):
    estimated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    results = []
    results += estimate_ec2_cost()
    results += estimate_rds_cost()
    results += estimate_ebs_cost()

    save_to_dynamodb(results, estimated_at)
    save_to_s3(results, estimated_at)

    if SLACK_WEBHOOK_URL:
        notify_slack(results, estimated_at)

    return {"statusCode": 200, "body": json.dumps({"services": len(results)})}


# ────────────────────────────────────────────────
# Athena — 실제 실행 시간 조회
# ────────────────────────────────────────────────
def get_running_hours_from_athena(namespace, dimension_key):
    """
    CloudWatch 메트릭 데이터를 Athena에서 조회해
    리소스별 실제 실행 시간(시간 단위)을 반환
    반환 형태: {"i-1234abcd": 312, "i-5678efgh": 720}
    """
    query = f"""
        SELECT
            json_extract_scalar(dimensions, '$.{dimension_key}') AS resource_id,
            COUNT(DISTINCT date_format(from_unixtime(timestamp / 1000), '%Y-%m-%d %H')) AS running_hours
        FROM {ATHENA_TABLE}
        WHERE namespace = '{namespace}'
          AND metric_name = 'CPUUtilization'
          AND from_unixtime(timestamp / 1000) >= date_add('day', -30, current_date)
        GROUP BY json_extract_scalar(dimensions, '$.{dimension_key}')
    """
    rows = _run_athena_query(query)
    return {row[0]: int(row[1]) for row in rows if row[0]}


def _run_athena_query(query):
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={"Database": ATHENA_DB},
        ResultConfiguration={"OutputLocation": ATHENA_RESULTS},
    )
    query_id = response["QueryExecutionId"]

    # 완료 대기
    while True:
        status = athena_client.get_query_execution(QueryExecutionId=query_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(2)

    if state != "SUCCEEDED":
        return []

    # 결과 수집 (첫 행은 헤더라서 제외)
    rows = []
    paginator = athena_client.get_paginator("get_query_results")
    first_page = True
    for page in paginator.paginate(QueryExecutionId=query_id):
        page_rows = page["ResultSet"]["Rows"]
        if first_page:
            page_rows = page_rows[1:]
            first_page = False
        for row in page_rows:
            rows.append([col.get("VarCharValue", "") for col in row["Data"]])
    return rows


# ────────────────────────────────────────────────
# EC2 비용 추정
# ────────────────────────────────────────────────
def estimate_ec2_cost():
    # Athena에서 실제 실행 시간 조회
    running_hours_map = get_running_hours_from_athena("AWS/EC2", "InstanceId")

    instances = []
    paginator = ec2_client.get_paginator("describe_instances")
    for page in paginator.paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    ):
        for reservation in page["Reservations"]:
            instances.extend(reservation["Instances"])

    if not instances:
        return []

    total_cost = 0.0
    breakdown = []
    for inst in instances:
        instance_id   = inst["InstanceId"]
        instance_type = inst["InstanceType"]
        hourly        = get_ec2_hourly_price(instance_type)

        # Athena 데이터 있으면 실제 시간, 없으면 기본값 720시간
        hours  = running_hours_map.get(instance_id, HOURS_PER_MONTH)
        monthly = round(hourly * hours, 4)
        total_cost += monthly
        breakdown.append({
            "instance_id":            instance_id,
            "instance_type":          instance_type,
            "hourly_usd":             hourly,
            "running_hours":          hours,
            "estimated_monthly_usd":  monthly,
        })

    return [{
        "service_name":           "EC2",
        "resource_count":         len(instances),
        "estimated_monthly_cost": round(total_cost, 4),
        "currency":               "USD",
        "is_anomaly":             total_cost > COST_THRESHOLD,
        "breakdown":              breakdown,
    }]


def get_ec2_hourly_price(instance_type):
    location = REGION_LOCATION.get(REGION, "Asia Pacific (Seoul)")
    try:
        response = pricing_client.get_products(
            ServiceCode="AmazonEC2",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "instanceType",    "Value": instance_type},
                {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                {"Type": "TERM_MATCH", "Field": "tenancy",         "Value": "Shared"},
                {"Type": "TERM_MATCH", "Field": "location",        "Value": location},
                {"Type": "TERM_MATCH", "Field": "preInstalledSw",  "Value": "NA"},
                {"Type": "TERM_MATCH", "Field": "capacitystatus",  "Value": "Used"},
            ],
            MaxResults=1,
        )
        return _parse_price(response)
    except Exception:
        return 0.0


# ────────────────────────────────────────────────
# RDS 비용 추정
# ────────────────────────────────────────────────
def estimate_rds_cost():
    running_hours_map = get_running_hours_from_athena("AWS/RDS", "DBInstanceIdentifier")

    instances = []
    paginator = rds_client.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page["DBInstances"]:
            if db["DBInstanceStatus"] == "available":
                instances.append(db)

    if not instances:
        return []

    total_cost = 0.0
    breakdown  = []
    for db in instances:
        db_id    = db["DBInstanceIdentifier"]
        db_class = db["DBInstanceClass"]
        engine   = db["Engine"]
        multi_az = db["MultiAZ"]
        hourly   = get_rds_hourly_price(db_class, engine, multi_az)

        hours   = running_hours_map.get(db_id, HOURS_PER_MONTH)
        monthly = round(hourly * hours, 4)
        total_cost += monthly
        breakdown.append({
            "db_identifier":         db_id,
            "db_class":              db_class,
            "engine":                engine,
            "multi_az":              multi_az,
            "hourly_usd":            hourly,
            "running_hours":         hours,
            "estimated_monthly_usd": monthly,
        })

    return [{
        "service_name":           "RDS",
        "resource_count":         len(instances),
        "estimated_monthly_cost": round(total_cost, 4),
        "currency":               "USD",
        "is_anomaly":             total_cost > COST_THRESHOLD,
        "breakdown":              breakdown,
    }]


def get_rds_hourly_price(db_class, engine, multi_az):
    location   = REGION_LOCATION.get(REGION, "Asia Pacific (Seoul)")
    deployment = "Multi-AZ" if multi_az else "Single-AZ"
    engine_map = {
        "mysql":       "MySQL",
        "postgres":    "PostgreSQL",
        "mariadb":     "MariaDB",
        "oracle-se2":  "Oracle",
        "sqlserver-se":"SQL Server",
    }
    db_engine = engine_map.get(engine, "PostgreSQL")
    try:
        response = pricing_client.get_products(
            ServiceCode="AmazonRDS",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "instanceType",     "Value": db_class},
                {"Type": "TERM_MATCH", "Field": "databaseEngine",   "Value": db_engine},
                {"Type": "TERM_MATCH", "Field": "deploymentOption", "Value": deployment},
                {"Type": "TERM_MATCH", "Field": "location",         "Value": location},
            ],
            MaxResults=1,
        )
        return _parse_price(response)
    except Exception:
        return 0.0


# ────────────────────────────────────────────────
# EBS 비용 추정 (연결된 볼륨 — 스토리지는 시간 무관)
# ────────────────────────────────────────────────
def estimate_ebs_cost():
    paginator = ec2_client.get_paginator("describe_volumes")
    volumes   = []
    for page in paginator.paginate(
        Filters=[{"Name": "status", "Values": ["in-use"]}]
    ):
        volumes.extend(page["Volumes"])

    if not volumes:
        return []

    PRICE_PER_GB = {
        "gp3": 0.08, "gp2": 0.10,
        "io1": 0.125, "io2": 0.125,
        "st1": 0.045, "sc1": 0.025,
    }
    total_cost = 0.0
    breakdown  = []
    for vol in volumes:
        vol_type  = vol["VolumeType"]
        size_gb   = vol["Size"]
        price_gb  = PRICE_PER_GB.get(vol_type, 0.08)
        monthly   = round(size_gb * price_gb, 4)
        total_cost += monthly
        breakdown.append({
            "volume_id":             vol["VolumeId"],
            "volume_type":           vol_type,
            "size_gb":               size_gb,
            "estimated_monthly_usd": monthly,
        })

    return [{
        "service_name":           "EBS",
        "resource_count":         len(volumes),
        "estimated_monthly_cost": round(total_cost, 4),
        "currency":               "USD",
        "is_anomaly":             total_cost > COST_THRESHOLD,
        "breakdown":              breakdown,
    }]


# ────────────────────────────────────────────────
# 공통 유틸
# ────────────────────────────────────────────────
def _parse_price(response):
    for price_str in response.get("PriceList", []):
        item = json.loads(price_str)
        for term in item.get("terms", {}).get("OnDemand", {}).values():
            for dim in term.get("priceDimensions", {}).values():
                price = float(dim["pricePerUnit"].get("USD", 0))
                if price > 0:
                    return price
    return 0.0


def save_to_dynamodb(results, estimated_at):
    table = dynamodb.Table(DYNAMODB_TABLE)
    ttl   = int(time.time()) + 90 * 24 * 60 * 60

    with table.batch_writer() as batch:
        for item in results:
            batch.put_item(Item={
                "service_name":           item["service_name"],
                "estimated_at":           estimated_at,
                "resource_count":         item["resource_count"],
                "estimated_monthly_cost": str(item["estimated_monthly_cost"]),
                "currency":               item["currency"],
                "is_anomaly":             item["is_anomaly"],
                "breakdown":              json.dumps(item["breakdown"], default=str),
                "ttl":                    ttl,
            })


def save_to_s3(results, estimated_at):
    if not results:
        return
    date_prefix = estimated_at[:10]
    key = f"{S3_PREFIX}{date_prefix}/results.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(results, ensure_ascii=False, default=str),
        ContentType="application/json",
    )


def notify_slack(results, estimated_at):
    import urllib.request

    total     = sum(r["estimated_monthly_cost"] for r in results)
    anomalies = [r for r in results if r["is_anomaly"]]

    lines = [f"*[Cost Estimator] {estimated_at}*"]
    lines.append(f"• 예상 월 총 비용: *${total:.2f} USD*")

    if anomalies:
        lines.append(f"\n*⚠️ 임계값 초과 ({len(anomalies)}건)*")
        for a in anomalies:
            lines.append(f"  - {a['service_name']}: ${a['estimated_monthly_cost']:.2f}")

    lines.append("\n*서비스별 예상 비용*")
    for r in results:
        lines.append(
            f"  - {r['service_name']}: ${r['estimated_monthly_cost']:.2f} "
            f"({r['resource_count']}개)"
        )

    payload = {"text": "\n".join(lines)}
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)
