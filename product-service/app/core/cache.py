import logging
import urllib.request

import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

_write_client: redis.Redis | None = None
_read_client: redis.Redis | None = None


def _detect_az() -> str:
    try:
        token_req = urllib.request.Request(
            "http://169.254.169.254/latest/api/token",
            data=b"",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "300"},
            method="PUT",
        )
        token = urllib.request.urlopen(token_req, timeout=1).read().decode()
        az_req = urllib.request.Request(
            "http://169.254.169.254/latest/meta-data/placement/availability-zone",
            headers={"X-aws-ec2-metadata-token": token},
        )
        return urllib.request.urlopen(az_req, timeout=1).read().decode()
    except Exception:
        return ""


def get_redis() -> redis.Redis | None:
    global _write_client
    if _write_client is not None:
        return _write_client
    if not settings.redis_url:
        return None
    try:
        _write_client = redis.from_url(
            settings.redis_url,
            ssl_cert_reqs=None,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        _write_client.ping()
        logger.info("Redis 쓰기 클라이언트 연결 성공 (Primary/AZ-2c)")
    except Exception as e:
        logger.warning("Redis 쓰기 클라이언트 연결 실패: %s", e)
        _write_client = None
    return _write_client


def get_redis_read() -> redis.Redis | None:
    global _read_client
    if _read_client is not None:
        return _read_client

    az = _detect_az()

    # Primary: AZ-2c / Replica: AZ-2a (실제 배치 기준)
    # AZ-2c 파드 → Primary endpoint (같은 AZ)
    # AZ-2a 파드 → Reader endpoint / Replica (같은 AZ)
    if "ap-northeast-2c" in az:
        read_url = settings.redis_url
        az_label = "AZ-2c → Primary (same AZ)"
    else:
        read_url = settings.redis_read_url or settings.redis_url
        az_label = f"AZ-2a → Replica (same AZ) / fallback (az={az!r})"

    if not read_url:
        return None
    try:
        _read_client = redis.from_url(
            read_url,
            ssl_cert_reqs=None,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        _read_client.ping()
        logger.info("Redis 읽기 클라이언트 연결 성공 (%s)", az_label)
    except Exception as e:
        logger.warning("Redis 읽기 클라이언트 연결 실패: %s", e)
        _read_client = None
    return _read_client
