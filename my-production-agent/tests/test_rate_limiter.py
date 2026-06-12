"""Unit tests — sliding window rate limiter (Redis ZSET)."""
import pytest
from fastapi import HTTPException

from app.config import settings
from app.rate_limiter import check_rate_limit


def test_under_limit_passes(fake_redis):
    for _ in range(settings.rate_limit_per_minute):
        check_rate_limit("user1")  # không raise


def test_over_limit_raises_429(fake_redis):
    for _ in range(settings.rate_limit_per_minute):
        check_rate_limit("user1")
    with pytest.raises(HTTPException) as exc:
        check_rate_limit("user1")
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_limit_is_per_user(fake_redis):
    for _ in range(settings.rate_limit_per_minute):
        check_rate_limit("user1")
    check_rate_limit("user2")  # user khác không bị ảnh hưởng


def test_old_requests_expire_from_window(fake_redis):
    import app.rate_limiter as rl
    real_time = rl.time.time()
    # 5 requests "cách đây 2 phút" — đã ngoài window 60s
    for i in range(5):
        fake_redis.zadd("ratelimit:user1", {f"old:{i}": real_time - 120})
    check_rate_limit("user1")  # không raise vì entries cũ bị dọn
