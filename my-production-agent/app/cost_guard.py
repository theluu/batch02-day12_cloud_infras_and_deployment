"""
Cost guard — budget $/tháng per user, tracking trong Redis.

Key `budget:{user}:{YYYY-MM}` giữ tổng chi tiêu tháng hiện tại,
expire 32 ngày nên tự reset sang tháng mới. Vượt budget → 402.
"""
from datetime import datetime, timezone

from fastapi import Depends, HTTPException

from .auth import verify_api_key
from .config import settings
from .redis_client import r

# Giá tham khảo gpt-4o-mini
PRICE_PER_1K_INPUT = 0.00015
PRICE_PER_1K_OUTPUT = 0.0006


def _month_key(user_id: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"budget:{user_id}:{month}"


def check_budget(user_id: str = Depends(verify_api_key)) -> None:
    spent = float(r.get(_month_key(user_id)) or 0)
    if spent >= settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "spent_usd": round(spent, 6),
                "budget_usd": settings.monthly_budget_usd,
                "resets": "đầu tháng sau (UTC)",
            },
        )


def record_usage(user_id: str, input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT
    key = _month_key(user_id)
    pipe = r.pipeline()
    pipe.incrbyfloat(key, cost)
    pipe.expire(key, 32 * 24 * 3600)
    spent, _ = pipe.execute()
    return float(spent)


def get_usage(user_id: str) -> dict:
    spent = float(r.get(_month_key(user_id)) or 0)
    return {
        "user_id": user_id,
        "month": datetime.now(timezone.utc).strftime("%Y-%m"),
        "spent_usd": round(spent, 6),
        "budget_usd": settings.monthly_budget_usd,
        "remaining_usd": round(max(0.0, settings.monthly_budget_usd - spent), 6),
    }
