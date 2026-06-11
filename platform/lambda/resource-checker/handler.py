import json
import os
import time
from datetime import datetime, timedelta, timezone

import boto3

DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_PREFIX = os.environ.get("S3_PREFIX", "raw/resource-check/")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
REGION = os.environ.get("AWS_REGION", "ap-northeast-2")

config_client = boto3.client("config", region_name=REGION)
ec2 = boto3.client("ec2", region_name=REGION)
rds = boto3.client("rds", region_name=REGION)
cw = boto3.client("cloudwatch", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)


def lambda_handler(event, context):
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = []

    results += check_unused_ebs()
    results += check_unattached_eip()
    results += check_old_snapshots()
    results += check_missing_tags()
    results += check_open_security_groups()
    results += check_low_utilization()

    save_to_dynamodb(results, checked_at)
    save_to_s3(results, checked_at)

    if SLACK_WEBHOOK_URL and results:
        notify_slack(results, checked_at)

    return {"statusCode": 200, "body": json.dumps({"checked": len(results)})}


# ────────────────────────────────────────────────
# AWS Config 공통 쿼리 헬퍼
# ────────────────────────────────────────────────
def _select_config(query):
    results = []
    paginator = config_client.get_paginator("select_resource_config")
    for page in paginator.paginate(Expression=query):
        for item in page["Results"]:
            results.append(json.loads(item))
    return results


# ────────────────────────────────────────────────
# Config 기반 점검 함수들
# ────────────────────────────────────────────────
def check_unused_ebs():
    items = _select_config(
        "SELECT resourceId, configuration "
        "WHERE resourceType = 'AWS::EC2::Volume' "
        "AND configuration.state.value = 'available'"
    )
    results = []
    for item in items:
        config = item.get("configuration", {})
        results.append({
            "resource_id": item["resourceId"],
            "resource_type": "EBS",
            "issue_type": "UNUSED",
            "region": REGION,
            "details": {
                "size_gb": str(config.get("size", "")),
                "volume_type": config.get("volumeType", ""),
                "created": str(config.get("createTime", "")),
            },
        })
    return results


def check_unattached_eip():
    items = _select_config(
        "SELECT resourceId, configuration "
        "WHERE resourceType = 'AWS::EC2::EIP'"
    )
    results = []
    for item in items:
        config = item.get("configuration", {})
        if not config.get("associationId"):  # null이면 미연결
            results.append({
                "resource_id": item["resourceId"],
                "resource_type": "EIP",
                "issue_type": "UNUSED",
                "region": REGION,
                "details": {
                    "public_ip": config.get("publicIp", ""),
                },
            })
    return results


def check_old_snapshots(days_threshold=30):
    items = _select_config(
        "SELECT resourceId, configuration, resourceCreationTime "
        "WHERE resourceType = 'AWS::EC2::Snapshot'"
    )
    now = datetime.now(timezone.utc)
    results = []
    for item in items:
        created_str = item.get("resourceCreationTime", "")
        if not created_str:
            continue
        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        age_days = (now - created).days
        if age_days >= days_threshold:
            config = item.get("configuration", {})
            results.append({
                "resource_id": item["resourceId"],
                "resource_type": "SNAPSHOT",
                "issue_type": "OLD_SNAPSHOT",
                "region": REGION,
                "details": {
                    "age_days": str(age_days),
                    "size_gb": str(config.get("volumeSize", "")),
                    "description": config.get("description", ""),
                },
            })
    return results


def check_missing_tags(required_tags=None):
    if required_tags is None:
        required_tags = ["Project", "Environment", "Owner"]

    items = _select_config(
        "SELECT resourceId, tags "
        "WHERE resourceType = 'AWS::EC2::Instance'"
    )
    results = []
    for item in items:
        tags = item.get("tags", {})  # Config는 태그를 {key: value} dict로 반환
        missing = [t for t in required_tags if t not in tags]
        if missing:
            results.append({
                "resource_id": item["resourceId"],
                "resource_type": "EC2",
                "issue_type": "NO_TAG",
                "region": REGION,
                "details": {
                    "missing_tags": json.dumps(missing),
                },
            })
    return results


def check_open_security_groups():
    items = _select_config(
        "SELECT resourceId, configuration "
        "WHERE resourceType = 'AWS::EC2::SecurityGroup'"
    )
    results = []
    for item in items:
        config = item.get("configuration", {})
        open_rules = []

        for rule in config.get("ipPermissions", []):
            for ip_range in rule.get("ipRanges", []):
                if ip_range.get("cidrIp") == "0.0.0.0/0":
                    open_rules.append({
                        "direction": "inbound",
                        "protocol": rule.get("ipProtocol", "all"),
                        "from_port": str(rule.get("fromPort", 0)),
                        "to_port": str(rule.get("toPort", 65535)),
                        "cidr": "0.0.0.0/0",
                    })
            for ipv6_range in rule.get("ipv6Ranges", []):
                if ipv6_range.get("cidrIpv6") == "::/0":
                    open_rules.append({
                        "direction": "inbound",
                        "protocol": rule.get("ipProtocol", "all"),
                        "from_port": str(rule.get("fromPort", 0)),
                        "to_port": str(rule.get("toPort", 65535)),
                        "cidr": "::/0",
                    })

        if open_rules:
            results.append({
                "resource_id": item["resourceId"],
                "resource_type": "SECURITY_GROUP",
                "issue_type": "OPEN_SECURITY_GROUP",
                "region": REGION,
                "details": {
                    "group_name": config.get("groupName", ""),
                    "vpc_id": config.get("vpcId", ""),
                    "open_rules": json.dumps(open_rules),
                    "open_rules_count": str(len(open_rules)),
                },
            })
    return results


# ────────────────────────────────────────────────
# CloudWatch 기반 (Config로 대체 불가 — CPU 메트릭)
# ────────────────────────────────────────────────
def check_low_utilization(cpu_threshold=10.0, days=7):
    results = []
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days)

    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    ):
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                avg_cpu = _get_average_cpu(
                    namespace="AWS/EC2",
                    dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                    start_time=start_time,
                    end_time=now,
                )
                if avg_cpu is not None and avg_cpu < cpu_threshold:
                    results.append({
                        "resource_id": instance_id,
                        "resource_type": "EC2",
                        "issue_type": "LOW_UTILIZATION",
                        "region": REGION,
                        "details": {
                            "avg_cpu_pct": str(round(avg_cpu, 2)),
                            "period_days": str(days),
                            "threshold_pct": str(cpu_threshold),
                            "instance_type": instance["InstanceType"],
                        },
                    })

    paginator = rds.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page["DBInstances"]:
            if db["DBInstanceStatus"] != "available":
                continue
            db_id = db["DBInstanceIdentifier"]
            avg_cpu = _get_average_cpu(
                namespace="AWS/RDS",
                dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
                start_time=start_time,
                end_time=now,
            )
            if avg_cpu is not None and avg_cpu < cpu_threshold:
                results.append({
                    "resource_id": db_id,
                    "resource_type": "RDS",
                    "issue_type": "LOW_UTILIZATION",
                    "region": REGION,
                    "details": {
                        "avg_cpu_pct": str(round(avg_cpu, 2)),
                        "period_days": str(days),
                        "threshold_pct": str(cpu_threshold),
                        "db_instance_class": db["DBInstanceClass"],
                        "engine": db["Engine"],
                    },
                })

    return results


def _get_average_cpu(namespace, dimensions, start_time, end_time):
    response = cw.get_metric_statistics(
        Namespace=namespace,
        MetricName="CPUUtilization",
        Dimensions=dimensions,
        StartTime=start_time,
        EndTime=end_time,
        Period=3600,
        Statistics=["Average"],
    )
    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return None
    return sum(d["Average"] for d in datapoints) / len(datapoints)


# ────────────────────────────────────────────────
# 저장 & 알림
# ────────────────────────────────────────────────
def save_to_dynamodb(results, checked_at):
    table = dynamodb.Table(DYNAMODB_TABLE)
    ttl = int(time.time()) + 90 * 24 * 60 * 60

    with table.batch_writer() as batch:
        for item in results:
            batch.put_item(Item={
                "resource_id": item["resource_id"],
                "checked_at": checked_at,
                "resource_type": item["resource_type"],
                "issue_type": item["issue_type"],
                "region": item["region"],
                "details": item["details"],
                "notified": False,
                "ttl": ttl,
            })


def save_to_s3(results, checked_at):
    if not results:
        return
    date_prefix = checked_at[:10]
    key = f"{S3_PREFIX}{date_prefix}/results.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(results, ensure_ascii=False, default=str),
        ContentType="application/json",
    )


def notify_slack(results, checked_at):
    import urllib.request

    summary = {}
    for r in results:
        summary[r["issue_type"]] = summary.get(r["issue_type"], 0) + 1

    lines = [f"*[Resource Checker] {checked_at}*"]
    for issue_type, count in summary.items():
        lines.append(f"• {issue_type}: {count}건")

    payload = {"text": "\n".join(lines)}
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)
