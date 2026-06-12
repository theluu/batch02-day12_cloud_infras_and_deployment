"""
Backend client — chuyển câu hỏi tới Legal Multi-Agent System qua A2A protocol.

Gateway (app.main) không gọi LLM trực tiếp nữa; nó forward tới Customer Agent
(entry point của mạng multi-agent: Customer → Law → Tax + Compliance song song).
"""
import os
from uuid import uuid4

import httpx

CUSTOMER_AGENT_URL = os.getenv("CUSTOMER_AGENT_URL", "http://localhost:10100")
AGENT_TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT_SECONDS", "300"))


def _build_a2a_payload(question: str) -> dict:
    """JSON-RPC message/send theo A2A protocol."""
    return {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": question}],
                "messageId": str(uuid4()),
            }
        },
    }


def _extract_text(result: dict) -> str:
    """Gom text từ artifacts (Task) hoặc parts (Message) trong response A2A."""
    chunks: list[str] = []
    for artifact in result.get("artifacts") or []:
        for part in artifact.get("parts") or []:
            if part.get("text"):
                chunks.append(part["text"])
    for part in result.get("parts") or []:
        if part.get("text"):
            chunks.append(part["text"])
    return "\n".join(chunks)


async def ask_llm(question: str, history: list[dict]) -> str:
    """Gửi câu hỏi tới Customer Agent, trả về phân tích pháp lý tổng hợp."""
    async with httpx.AsyncClient(timeout=AGENT_TIMEOUT_SECONDS) as client:
        resp = await client.post(CUSTOMER_AGENT_URL, json=_build_a2a_payload(question))
        resp.raise_for_status()
        data = resp.json()

    if "error" in data:
        raise RuntimeError(f"A2A error: {data['error']}")

    text = _extract_text(data.get("result") or {})
    return text or "(agent network returned no text)"


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()) * 2)
