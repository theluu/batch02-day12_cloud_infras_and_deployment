"""
Rate limiting — Sliding Window bằng Redis ZSET.

Mỗi user một sorted set `ratelimit:{user}`, score = timestamp.
Mỗi request: xóa entries cũ hơn 60s → đếm → nếu đủ limit thì 429.
Dùng Redis (không phải in-memory) nên hoạt động đúng khi scale nhiều instances.
"""
import time
import uuid

from fastapi import Depends, HTTPException

from .auth import verify_api_key
from .config import settings
from .redis_client import r

WINDOW_SECONDS = 60


def check_rate_limit(user_id: str = Depends(verify_api_key)) -> None:
    now = time.time()
    key = f"ratelimit:{user_id}"
    limit = settings.rate_limit_per_minute

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
    pipe.zcard(key)
    _, current = pipe.execute()

    if current >= limit:
        oldest = r.zrange(key, 0, 0, withscores=True)
        retry_after = int(oldest[0][1] + WINDOW_SECONDS - now) + 1 if oldest else WINDOW_SECONDS
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit_per_minute": limit,
                "retry_after_seconds": retry_after,
            },
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(retry_after),
            },
        )

    pipe = r.pipeline()
    pipe.zadd(key, {f"{now}:{uuid.uuid4().hex[:8]}": now})
    pipe.expire(key, WINDOW_SECONDS + 5)
    pipe.execute()
