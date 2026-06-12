"""Unit tests — monthly budget cost guard."""
import pytest
from fastapi import HTTPException

from app.cost_guard import check_budget, get_usage, record_usage


def test_under_budget_passes(fake_redis):
    check_budget("user1")  # chưa tiêu gì → không raise


def test_record_usage_accumulates(fake_redis):
    spent1 = record_usage("user1", input_tokens=1000, output_tokens=1000)
    spent2 = record_usage("user1", input_tokens=1000, output_tokens=1000)
    assert spent2 == pytest.approx(spent1 * 2)


def test_over_budget_raises_402(fake_redis):
    from app.cost_guard import _month_key
    fake_redis.set(_month_key("user1"), "10.5")  # vượt budget $10
    with pytest.raises(HTTPException) as exc:
        check_budget("user1")
    assert exc.value.status_code == 402


def test_get_usage_reports_remaining(fake_redis):
    from app.cost_guard import _month_key
    fake_redis.set(_month_key("user1"), "4.0")
    usage = get_usage("user1")
    assert usage["spent_usd"] == 4.0
    assert usage["remaining_usd"] == 6.0


def test_budget_is_per_user(fake_redis):
    from app.cost_guard import _month_key
    fake_redis.set(_month_key("user1"), "99")
    check_budget("user2")  # user khác vẫn còn budget
