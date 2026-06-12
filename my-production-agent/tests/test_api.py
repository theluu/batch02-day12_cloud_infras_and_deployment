"""Integration tests — API endpoints qua TestClient."""


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ready_returns_200_when_redis_ok(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["ready"] is True


def test_ask_without_key_returns_401(client):
    resp = client.post("/ask", json={"question": "Hello"})
    assert resp.status_code == 401


def test_ask_with_invalid_key_returns_401(client):
    resp = client.post("/ask", json={"question": "Hello"},
                       headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_ask_with_valid_key_returns_answer(client):
    resp = client.post("/ask", json={"question": "Hello"},
                       headers={"X-API-Key": "alice-key"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert body["session_id"]
    assert body["usage"]["month_spent_usd"] > 0


def test_conversation_history_persists_across_turns(client):
    r1 = client.post("/ask", json={"question": "Turn 1"},
                     headers={"X-API-Key": "alice-key"})
    sid = r1.json()["session_id"]
    client.post("/ask", json={"question": "Turn 2", "session_id": sid},
                headers={"X-API-Key": "alice-key"})
    hist = client.get(f"/history/{sid}", headers={"X-API-Key": "alice-key"})
    assert hist.status_code == 200
    assert hist.json()["count"] == 4  # 2 turns × (user + assistant)


def test_ask_rate_limited_returns_429(client):
    for _ in range(5):  # RATE_LIMIT_PER_MINUTE=5 trong test env
        client.post("/ask", json={"question": "x"},
                    headers={"X-API-Key": "bob-key"})
    resp = client.post("/ask", json={"question": "x"},
                       headers={"X-API-Key": "bob-key"})
    assert resp.status_code == 429


def test_ask_over_budget_returns_402(client, fake_redis):
    from app.cost_guard import _month_key
    fake_redis.set(_month_key("alice"), "10.5")
    resp = client.post("/ask", json={"question": "x"},
                       headers={"X-API-Key": "alice-key"})
    assert resp.status_code == 402


def test_usage_endpoint(client):
    resp = client.get("/usage", headers={"X-API-Key": "alice-key"})
    assert resp.status_code == 200
    assert resp.json()["budget_usd"] == 10.0


def test_empty_question_rejected(client):
    resp = client.post("/ask", json={"question": ""},
                       headers={"X-API-Key": "alice-key"})
    assert resp.status_code == 422
