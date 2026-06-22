"""
resource-checker/handler.py 테스트
- EBS/EIP/Snapshot/Tag/SG/RDS 점검 로직 + DDB 적재
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# 환경변수 설정 (handler 로드 전)
os.environ.setdefault("TABLE_NAME", "test-check-results")
os.environ.setdefault("BUCKET_NAME", "test-bucket")
os.environ.setdefault("SNAPSHOT_AGE_DAYS", "30")

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_aws_clients():
    with patch("handler.ec2") as mock_ec2, \
         patch("handler.rds") as mock_rds, \
         patch("handler.ddb") as mock_ddb, \
         patch("handler.s3") as mock_s3:
        yield {"ec2": mock_ec2, "rds": mock_rds, "ddb": mock_ddb, "s3": mock_s3}


# ─────────────────────────────────────────────────────────────────────────────
# Unused EBS 검출
# ─────────────────────────────────────────────────────────────────────────────

def test_find_unused_ebs_detects_unattached(mock_aws_clients):
    """available 상태(미연결) EBS 찾기"""
    from handler import find_unused_ebs

    mock_aws_clients["ec2"].describe_volumes.return_value = {
        "Volumes": [
            {"VolumeId": "vol-abc", "State": "available", "Size": 10},
        ]
    }

    findings = find_unused_ebs()

    assert len(findings) == 1
    assert findings[0]["resourceId"] == "vol-abc"
    assert findings[0]["checkType"] == "UNUSED_RESOURCE"
    assert findings[0]["resourceType"] == "EBS"


def test_find_unused_ebs_skips_in_use(mock_aws_clients):
    """available filter 통과 못한 경우 빈 결과 (describe_volumes filter='available')"""
    from handler import find_unused_ebs

    # 실제 핸들러는 Filters=[{Name:status, Values:[available]}] 호출
    # → in-use 볼륨은 응답에 안 옴 (= 빈 리스트)
    mock_aws_clients["ec2"].describe_volumes.return_value = {"Volumes": []}

    findings = find_unused_ebs()

    assert findings == []


# ─────────────────────────────────────────────────────────────────────────────
# Unused EIP 검출
# ─────────────────────────────────────────────────────────────────────────────

def test_find_unused_eip_detects_unassociated(mock_aws_clients):
    """연결 안 된 EIP 검출"""
    from handler import find_unused_eip

    mock_aws_clients["ec2"].describe_addresses.return_value = {
        "Addresses": [
            {"AllocationId": "eipalloc-abc", "PublicIp": "1.2.3.4"},
            # AssociationId 없음 = unassociated
        ]
    }

    findings = find_unused_eip()

    assert len(findings) == 1
    assert findings[0]["resourceType"] == "EIP"
    assert findings[0]["checkType"] == "UNUSED_RESOURCE"


def test_find_unused_eip_skips_associated(mock_aws_clients):
    """연결된 EIP는 검출 안 함"""
    from handler import find_unused_eip

    mock_aws_clients["ec2"].describe_addresses.return_value = {
        "Addresses": [
            {
                "AllocationId": "eipalloc-attached",
                "PublicIp": "5.6.7.8",
                "AssociationId": "assoc-xyz",
            },
        ]
    }

    findings = find_unused_eip()
    assert findings == []


# ─────────────────────────────────────────────────────────────────────────────
# 오래된 Snapshot 검출
# ─────────────────────────────────────────────────────────────────────────────

def test_find_old_snapshots(mock_aws_clients):
    """SNAPSHOT_AGE_DAYS 초과한 스냅샷 검출"""
    from handler import find_old_snapshots

    old_date = datetime.now(timezone.utc) - timedelta(days=60)
    new_date = datetime.now(timezone.utc) - timedelta(days=5)

    mock_aws_clients["ec2"].describe_snapshots.return_value = {
        "Snapshots": [
            {"SnapshotId": "snap-old", "StartTime": old_date, "VolumeSize": 50},
            {"SnapshotId": "snap-new", "StartTime": new_date, "VolumeSize": 50},
        ]
    }

    findings = find_old_snapshots()

    assert len(findings) == 1
    assert findings[0]["resourceId"] == "snap-old"


# ─────────────────────────────────────────────────────────────────────────────
# 태그 누락 검출
# ─────────────────────────────────────────────────────────────────────────────

def test_find_missing_tags_detects_ec2(mock_aws_clients):
    """필수 태그 누락된 EC2 검출 — ec2.get_paginator 사용"""
    from handler import find_missing_tags

    # EC2 는 paginator 로 호출됨
    paginator = MagicMock()
    paginator.paginate.return_value = [{
        "Reservations": [{
            "Instances": [{
                "InstanceId": "i-notagged",
                "State": {"Name": "running"},
                "Tags": [{"Key": "Name", "Value": "test"}],  # Project, Env, Owner 없음
            }]
        }]
    }]
    mock_aws_clients["ec2"].get_paginator.return_value = paginator
    mock_aws_clients["ec2"].describe_volumes.return_value = {"Volumes": []}
    mock_aws_clients["ec2"].describe_snapshots.return_value = {"Snapshots": []}
    mock_aws_clients["rds"].describe_db_instances.return_value = {"DBInstances": []}

    findings = find_missing_tags()

    ec2_findings = [f for f in findings if f["resourceType"] == "EC2"]
    assert len(ec2_findings) == 1
    assert ec2_findings[0]["checkType"] == "MISSING_TAGS"


def test_find_missing_tags_all_present_skipped(mock_aws_clients):
    """모든 필수 태그 있으면 검출 안 함"""
    from handler import find_missing_tags

    full_tags = [
        {"Key": "Name", "Value": "test"},
        {"Key": "Project", "Value": "fiveline"},
        {"Key": "Environment", "Value": "dev"},
        {"Key": "Owner", "Value": "jihoo"},
    ]
    paginator = MagicMock()
    paginator.paginate.return_value = [{
        "Reservations": [{
            "Instances": [{
                "InstanceId": "i-tagged",
                "State": {"Name": "running"},
                "Tags": full_tags,
            }]
        }]
    }]
    mock_aws_clients["ec2"].get_paginator.return_value = paginator
    mock_aws_clients["ec2"].describe_volumes.return_value = {"Volumes": []}
    mock_aws_clients["ec2"].describe_snapshots.return_value = {"Snapshots": []}
    mock_aws_clients["rds"].describe_db_instances.return_value = {"DBInstances": []}

    findings = find_missing_tags()
    assert findings == []


# ─────────────────────────────────────────────────────────────────────────────
# 공개 SG 검출
# ─────────────────────────────────────────────────────────────────────────────

def test_find_open_security_groups(mock_aws_clients):
    """0.0.0.0/0 으로 open된 SG 검출"""
    from handler import find_open_security_groups

    mock_aws_clients["ec2"].describe_security_groups.return_value = {
        "SecurityGroups": [{
            "GroupId": "sg-open",
            "GroupName": "open-sg",
            "IpPermissions": [{
                "FromPort": 22,
                "ToPort": 22,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }],
        }]
    }

    findings = find_open_security_groups()

    assert len(findings) == 1
    assert findings[0]["resourceId"] == "sg-open"
    assert findings[0]["checkType"] == "SECURITY_RISK"


def test_find_open_sg_skips_private(mock_aws_clients):
    """프라이빗 CIDR 만 있는 SG는 무시"""
    from handler import find_open_security_groups

    mock_aws_clients["ec2"].describe_security_groups.return_value = {
        "SecurityGroups": [{
            "GroupId": "sg-private",
            "GroupName": "private",
            "IpPermissions": [{
                "FromPort": 22,
                "ToPort": 22,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "10.0.0.0/8"}],
            }],
        }]
    }

    findings = find_open_security_groups()
    assert findings == []


# ─────────────────────────────────────────────────────────────────────────────
# Public RDS 검출
# ─────────────────────────────────────────────────────────────────────────────

def test_find_public_rds(mock_aws_clients):
    """PubliclyAccessible=True 인 RDS 검출"""
    from handler import find_public_rds

    mock_aws_clients["rds"].describe_db_instances.return_value = {
        "DBInstances": [{
            "DBInstanceIdentifier": "rds-public",
            "PubliclyAccessible": True,
            "Engine": "postgres",
        }]
    }

    findings = find_public_rds()

    assert len(findings) == 1
    assert findings[0]["resourceId"] == "rds-public"
    assert findings[0]["checkType"] == "SECURITY_RISK"


def test_find_public_rds_skips_private(mock_aws_clients):
    """private RDS 는 무시"""
    from handler import find_public_rds

    mock_aws_clients["rds"].describe_db_instances.return_value = {
        "DBInstances": [{
            "DBInstanceIdentifier": "rds-private",
            "PubliclyAccessible": False,
        }]
    }

    findings = find_public_rds()
    assert findings == []
