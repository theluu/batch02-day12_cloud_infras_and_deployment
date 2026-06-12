"""
Production-ready AI Agent — Day 12 Final Project.

✅ API key auth · rate limit · cost guard · health/ready ·
   graceful shutdown (SIGTERM) · stateless (Redis) · JSON logging
"""
import json
import logging
import signal
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import verify_api_key
from .config import settings
from .cost_guard import check_budget, get_usage, record_usage
from .llm import ask_llm, estimate_tokens
from .rate_limiter import check_rate_limit
from .redis_client import r

# ── Structured JSON logging ─────────────────────────────────


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        })


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=settings.log_level, handlers=[handler])
logger = logging.getLogger("agent")

START_TIME = time.time()
INSTANCE_ID = f"instance-{uuid.uuid4().hex[:6]}"
_is_ready = False
_in_flight = 0

HISTORY_MAX_MESSAGES = 20
HISTORY_TTL_SECONDS = 3600


# ── Lifecycle: startup / graceful shutdown ──────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({"event": "startup", "instance": INSTANCE_ID,
                            "env": settings.environment, "port": settings.port}))
    _is_ready = True
    yield
    _is_ready = False
    waited = 0.0
    while _in_flight > 0 and waited < 30:
        time.sleep(0.5)
        waited += 0.5
    logger.info(json.dumps({"event": "shutdown_complete", "instance": INSTANCE_ID,
                            "waited_seconds": waited}))


_prev_sigterm = signal.getsignal(signal.SIGTERM)


def handle_sigterm(signum, frame):
    """SIGTERM từ orchestrator: log rồi chuyển cho handler của uvicorn
    để graceful shutdown (lifespan chờ in-flight requests)."""
    logger.info(json.dumps({"event": "sigterm_received", "instance": INSTANCE_ID}))
    if callable(_prev_sigterm):
        _prev_sigterm(signum, frame)


signal.signal(signal.SIGTERM, handle_sigterm)

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)


@app.middleware("http")
async def track_in_flight(request, call_next):
    global _in_flight
    _in_flight += 1
    try:
        return await call_next(request)
    finally:
        _in_flight -= 1


# ── Models ──────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None


# ── Conversation history (state trong Redis — stateless app) ─

def load_history(session_id: str) -> list[dict]:
    raw = r.lrange(f"history:{session_id}", 0, -1)
    return [json.loads(m) for m in raw]


def append_history(session_id: str, role: str, content: str) -> None:
    key = f"history:{session_id}"
    pipe = r.pipeline()
    pipe.rpush(key, json.dumps({"role": role, "content": content,
                                "ts": datetime.now(timezone.utc).isoformat()}))
    pipe.ltrim(key, -HISTORY_MAX_MESSAGES, -1)
    pipe.expire(key, HISTORY_TTL_SECONDS)
    pipe.execute()


# ── Endpoints ───────────────────────────────────────────────

@app.get("/")
def root():
    return {"app": settings.app_name, "version": settings.app_version,
            "docs": "/docs", "health": "/health", 
              "message": "Deployed by CI/CD pipeline 🚀"}


@app.post("/ask")
def ask(
    body: AskRequest,
    user_id: str = Depends(verify_api_key),
    _rate: None = Depends(check_rate_limit),
    _budget: None = Depends(check_budget),
):
    session_id = body.session_id or str(uuid.uuid4())
    history = load_history(session_id)

    answer = ask_llm(body.question, history)

    append_history(session_id, "user", body.question)
    append_history(session_id, "assistant", answer)

    input_tokens = estimate_tokens(body.question)
    output_tokens = estimate_tokens(answer)
    spent = record_usage(user_id, input_tokens, output_tokens)

    logger.info(json.dumps({
        "event": "agent_request", "user": user_id, "session": session_id,
        "question_length": len(body.question), "spent_usd": round(spent, 6),
        "instance": INSTANCE_ID,
    }))

    return {
        "session_id": session_id,
        "question": body.question,
        "answer": answer,
        "model": settings.llm_model,
        "served_by": INSTANCE_ID,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                  "month_spent_usd": round(spent, 6)},
    }


@app.get("/history/{session_id}")
def history(session_id: str, user_id: str = Depends(verify_api_key)):
    messages = load_history(session_id)
    if not messages:
        raise HTTPException(404, "Session not found or expired")
    return {"session_id": session_id, "messages": messages, "count": len(messages)}


@app.get("/usage")
def usage(user_id: str = Depends(verify_api_key)):
    return get_usage(user_id)


# ── Health checks ───────────────────────────────────────────

@app.get("/health")
def health():
    """Liveness probe — process còn sống không?"""
    return {
        "status": "ok",
        "instance": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/ready")
def ready():
    """Readiness probe — Redis OK và app đã khởi động xong chưa?"""
    if not _is_ready:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "reason": "starting up or shutting down"},
        )
    try:
        r.ping()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "reason": "redis unavailable"},
        )
    return {"ready": True, "instance": INSTANCE_ID, "in_flight_requests": _in_flight}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port,
                timeout_graceful_shutdown=30)
