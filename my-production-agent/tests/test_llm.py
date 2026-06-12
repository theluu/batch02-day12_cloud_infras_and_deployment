"""Unit tests — A2A client tới Customer Agent (app/llm.py)."""
import asyncio

import httpx
import pytest

import app.llm as llm


def test_build_a2a_payload_shape():
    payload = llm._build_a2a_payload("What is tort law?")
    assert payload["jsonrpc"] == "2.0"
    assert payload["method"] == "message/send"
    msg = payload["params"]["message"]
    assert msg["role"] == "user"
    assert msg["parts"][0]["text"] == "What is tort law?"
    assert msg["messageId"]


def test_extract_text_from_task_artifacts():
    result = {"artifacts": [{"parts": [{"text": "part1"}, {"text": "part2"}]}]}
    assert llm._extract_text(result) == "part1\npart2"


def test_extract_text_from_message_parts():
    result = {"parts": [{"kind": "text", "text": "direct message"}]}
    assert llm._extract_text(result) == "direct message"


def test_extract_text_empty():
    assert llm._extract_text({}) == ""


def _patch_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    orig_client = httpx.AsyncClient

    def factory(**kwargs):
        kwargs.pop("timeout", None)
        return orig_client(transport=transport)

    monkeypatch.setattr(llm.httpx, "AsyncClient", factory)


def test_ask_llm_returns_aggregated_text(monkeypatch):
    def handler(request):
        body = {"jsonrpc": "2.0", "id": "1",
                "result": {"artifacts": [{"parts": [{"text": "legal analysis"}]}]}}
        return httpx.Response(200, json=body)

    _patch_transport(monkeypatch, handler)
    answer = asyncio.run(llm.ask_llm("question", []))
    assert answer == "legal analysis"


def test_ask_llm_raises_on_a2a_error(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": "1",
                                         "error": {"code": -32000, "message": "boom"}})

    _patch_transport(monkeypatch, handler)
    with pytest.raises(RuntimeError):
        asyncio.run(llm.ask_llm("question", []))


def test_ask_llm_raises_on_http_error(monkeypatch):
    def handler(request):
        return httpx.Response(503)

    _patch_transport(monkeypatch, handler)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(llm.ask_llm("question", []))


def test_estimate_tokens():
    assert llm.estimate_tokens("one two three") == 6
    assert llm.estimate_tokens("") == 1
