"""
LLM client — mặc định mock (không cần API key thật).
Set OPENAI_API_KEY để thay bằng client thật.
"""
import hashlib

from .config import settings

_CANNED = [
    "Đây là câu trả lời từ AI agent. Trong production, đây sẽ là response từ LLM thật.",
    "Agent đang hoạt động tốt! Hệ thống đã được containerize và deploy lên cloud.",
    "Câu hỏi hay! Stateless design giúp hệ thống scale ngang dễ dàng.",
    "Docker + Redis + Nginx = một stack production-ready cho AI agent.",
]


def ask_llm(question: str, history: list[dict]) -> str:
    if settings.openai_api_key:
        # Chỗ này gắn OpenAI/Anthropic client thật khi có key
        pass
    idx = int(hashlib.md5(question.encode()).hexdigest(), 16) % len(_CANNED)
    answer = _CANNED[idx]
    if history:
        answer += f" (context: {len(history)} messages trước đó)"
    return answer


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()) * 2)
