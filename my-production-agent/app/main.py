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
from fastapi.responses import HTMLResponse, JSONResponse
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

# Trang chủ — ops-terminal dashboard, data lấy client-side từ /health
HOME_HTML = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>my-production-agent — control room</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;700&family=IBM+Plex+Mono:wght@400;600&display=swap"
      rel="stylesheet">
<style>
:root{
  --bg:#070b0a; --panel:#0d1412; --line:#1c2a26; --txt:#c9d6d1; --dim:#5d716a;
  --ok:#2bd97c; --warn:#ffb454; --err:#ff5d5d; --accent:#54e6c1;
}
*{box-sizing:border-box;margin:0}
body{
  background:var(--bg); color:var(--txt); min-height:100vh; padding:48px 20px;
  font-family:"IBM Plex Mono",monospace; font-size:14px; line-height:1.6;
  background-image:
    linear-gradient(var(--line) 1px, transparent 1px),
    linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size:42px 42px; background-position:center;
}
main{max-width:880px;margin:0 auto}
.crt{position:fixed;inset:0;pointer-events:none;opacity:.5;
  background:repeating-linear-gradient(0deg,transparent 0 2px,rgba(0,0,0,.25) 2px 4px)}
header{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:8px}
h1{font-family:"Chakra Petch",sans-serif;font-size:clamp(26px,5vw,44px);
   letter-spacing:.02em;color:#fff}
h1 .cursor{display:inline-block;width:.55em;height:1em;background:var(--ok);
   vertical-align:-.12em;animation:blink 1.1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.sub{color:var(--dim);margin-bottom:34px}
.sub b{color:var(--accent);font-weight:600}
.badge{display:inline-flex;align-items:center;gap:8px;padding:4px 12px;
  border:1px solid var(--line);border-radius:999px;background:var(--panel)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--warn)}
.dot.ok{background:var(--ok);box-shadow:0 0 10px var(--ok);animation:pulse 2s infinite}
@keyframes pulse{50%{box-shadow:0 0 2px var(--ok)}}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:1px;background:var(--line);border:1px solid var(--line);margin-bottom:34px}
.cell{background:var(--panel);padding:16px 18px}
.cell .k{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.18em}
.cell .v{font-family:"Chakra Petch",sans-serif;font-size:22px;color:#fff;margin-top:4px}
.cell .v.ok{color:var(--ok)}
section{border:1px solid var(--line);background:var(--panel);padding:24px;margin-bottom:26px}
section h2{font-family:"Chakra Petch",sans-serif;font-size:13px;color:var(--accent);
  text-transform:uppercase;letter-spacing:.24em;margin-bottom:18px}
section h2::before{content:"// "}
label{display:block;color:var(--dim);font-size:12px;margin:14px 0 6px}
input{width:100%;background:var(--bg);border:1px solid var(--line);color:var(--txt);
  padding:11px 13px;font:inherit;outline:none;transition:border-color .15s}
input:focus{border-color:var(--accent)}
button{margin-top:18px;width:100%;padding:13px;font-family:"Chakra Petch",sans-serif;
  font-size:15px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
  background:var(--ok);color:#04130b;border:0;cursor:pointer;transition:transform .08s}
button:hover{transform:translateY(-1px);box-shadow:0 0 24px rgba(43,217,124,.35)}
button:disabled{background:var(--dim);cursor:wait}
pre{background:var(--bg);border:1px dashed var(--line);padding:16px;margin-top:18px;
  white-space:pre-wrap;word-break:break-word;color:var(--accent);min-height:52px}
pre.err{color:var(--err);border-color:var(--err)}
nav{display:flex;gap:22px;flex-wrap:wrap;color:var(--dim);font-size:13px}
nav a{color:var(--txt);text-decoration:none;border-bottom:1px solid var(--line)}
nav a:hover{color:var(--ok);border-color:var(--ok)}
footer{margin-top:30px;color:var(--dim);font-size:12px}
footer b{color:var(--warn)}
</style>
</head>
<body>
<div class="crt"></div>
<main>
  <header>
    <h1>my-production-agent<span class="cursor"></span></h1>
    <span class="badge"><span id="dot" class="dot"></span><span id="st">checking…</span></span>
  </header>
  <p class="sub">AI agent · <b>Docker</b> → <b>GitHub Actions</b> → <b>Railway</b> ·
     auth / rate-limit / cost-guard / stateless-redis</p>

  <div class="grid">
    <div class="cell"><div class="k">status</div><div id="v-st" class="v">—</div></div>
    <div class="cell"><div class="k">version</div><div id="v-ver" class="v">—</div></div>
    <div class="cell"><div class="k">uptime</div><div id="v-up" class="v">—</div></div>
    <div class="cell"><div class="k">instance</div><div id="v-in" class="v">—</div></div>
  </div>

  <section>
    <h2>thử agent ngay tại đây</h2>
    <label for="key">x-api-key</label>
    <input id="key" placeholder="dán API key của bạn" autocomplete="off">
    <label for="q">question</label>
    <input id="q" value="Xin chào agent!" autocomplete="off">
    <button id="go">POST /ask ▸</button>
    <pre id="out">// response sẽ hiện ở đây</pre>
  </section>

  <nav>
    <a href="/docs">/docs — Swagger UI</a>
    <a href="/health">/health</a>
    <a href="/ready">/ready</a>
  </nav>
  <footer>không có key? request sẽ trả <b>401</b> — đó là tính năng, không phải bug.</footer>
</main>
<script>
async function health(){
  try{
    const r = await fetch('/health'); const d = await r.json();
    dot.className = 'dot ok'; st.textContent = 'LIVE';
    document.getElementById('v-st').textContent = d.status.toUpperCase();
    document.getElementById('v-st').className = 'v ok';
    document.getElementById('v-ver').textContent = 'v' + d.version;
    const s = Math.round(d.uptime_seconds);
    document.getElementById('v-up').textContent =
      s < 120 ? s + 's' : Math.round(s/60) + 'm';
    document.getElementById('v-in').textContent = d.instance.replace('instance-','');
  }catch(e){ dot.className = 'dot'; st.textContent = 'UNREACHABLE'; }
}
health(); setInterval(health, 5000);
go.onclick = async () => {
  go.disabled = true; out.className = ''; out.textContent = '// đang gọi…';
  try{
    const r = await fetch('/ask', {method:'POST',
      headers:{'Content-Type':'application/json','X-API-Key':key.value},
      body: JSON.stringify({question: q.value})});
    const d = await r.json();
    out.className = r.ok ? '' : 'err';
    out.textContent = 'HTTP ' + r.status + '\\n' + JSON.stringify(d, null, 2);
  }catch(e){ out.className = 'err'; out.textContent = '// ' + e; }
  go.disabled = false;
};
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def root():
    return HOME_HTML


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
        "message": "Hello from my-production-agent! "
                   "Visit /ready to check Redis connectivity and readiness.",
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
