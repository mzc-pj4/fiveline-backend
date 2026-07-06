import logging

import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

_write_client: redis.Redis | None = None
_read_client: redis.Redis | None = None


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
        logger.info("Redis 쓰기 클라이언트 연결 성공 (Primary)")
    except Exception as e:
        logger.warning("Redis 쓰기 클라이언트 연결 실패: %s", e)
        _write_client = None
    return _write_client


def get_redis_read() -> redis.Redis | None:
    global _read_client
    if _read_client is not None:
        return _read_client
    read_url = settings.redis_read_url or settings.redis_url
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
        logger.info("Redis 읽기 클라이언트 연결 성공 (Replica)")
    except Exception as e:
        logger.warning("Redis 읽기 클라이언트 연결 실패: %s", e)
        _read_client = None
    return _read_client
