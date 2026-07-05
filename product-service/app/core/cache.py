import logging

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def get_redis() -> redis.Redis | None:
    global _client
    if _client is not None:
        return _client
    if not settings.redis_url:
        return None
    try:
        _client = redis.from_url(
            settings.redis_url,
            ssl_cert_reqs=None,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        _client.ping()
        logger.info("Redis 연결 성공")
    except Exception as e:
        logger.warning("Redis 연결 실패, 캐시 비활성화: %s", e)
        _client = None
    return _client
