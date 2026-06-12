"""
Test fixtures — dùng fakeredis thay Redis thật để CI chạy không cần service ngoài.
Env vars phải set TRƯỚC khi import app (Settings đọc env lúc import).
"""
import os

os.environ.setdefault("AGENT_API_KEY", "test-key")
os.environ.setdefault("AGENT_API_KEYS", "alice-key:alice,bob-key:bob")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "5")
os.environ.setdefault("MONTHLY_BUDGET_USD", "10")

import fakeredis
import pytest
from fastapi.testclient import TestClient

import app.cost_guard as cost_guard_mod
import app.main as main_mod
import app.rate_limiter as rate_limiter_mod


@pytest.fixture()
def fake_redis(monkeypatch):
    r = fakeredis.FakeRedis(decode_responses=True)
    # patch mọi module đã import `r` bằng from-import
    monkeypatch.setattr(rate_limiter_mod, "r", r)
    monkeypatch.setattr(cost_guard_mod, "r", r)
    monkeypatch.setattr(main_mod, "r", r)
    return r


@pytest.fixture()
def client(fake_redis, monkeypatch):
    # Backend thật là mạng multi-agent (A2A) — mock trong unit tests
    async def fake_ask_llm(question: str, history: list[dict]) -> str:
        return f"[legal-multiagent] analysis of: {question}"

    monkeypatch.setattr(main_mod, "ask_llm", fake_ask_llm)
    with TestClient(main_mod.app) as c:
        yield c
