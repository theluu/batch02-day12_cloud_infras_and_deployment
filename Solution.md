# Solution — Day 12 Code Lab: Cloud Infrastructure & Deployment

> Đáp án chi tiết Part 1 → 5. Mọi kết quả bên dưới đều đã chạy và kiểm chứng thật,
> không phải đáp án lý thuyết. Final Project (Part 6) nằm tại `my-production-agent/`.

---

## Part 1: Localhost vs Production

### Exercise 1.1 — Anti-patterns trong `01-localhost-vs-production/develop/app.py`

Đề yêu cầu tìm ≥5, tìm được **8**:

| # | Anti-pattern | Code | Hậu quả |
|---|---|---|---|
| 1 | Hardcode secrets | `OPENAI_API_KEY = "sk-hardcoded..."`, `DATABASE_URL = "postgresql://admin:password123@..."` | Push GitHub là lộ key + password DB; đổi key phải sửa code |
| 2 | Log ra secret | `print(f"Using key: {OPENAI_API_KEY}")` | Key nằm trong log — ai đọc log là có key |
| 3 | `print()` thay vì logging | `print(f"[DEBUG] ...")` | Không level, không timestamp, không parse được bởi log aggregator |
| 4 | Không có health check | `curl /health` → **404** (đã test) | App crash, platform không biết để restart |
| 5 | Port cứng | `port=8000` | Railway/Render inject `PORT` động → app không nhận traffic |
| 6 | Bind `localhost` | `host="localhost"` | Trong container chỉ nghe loopback — traffic ngoài không tới được |
| 7 | Debug mode trong prod | `reload=True` | Tốn tài nguyên, behavior không ổn định |
| 8 | Không config management / graceful shutdown | `DEBUG=True` rải trong code, không xử lý SIGTERM | Request đang chạy bị chém ngang khi platform tắt container |

### Exercise 1.2 — Chạy bản basic

Chạy được, `/ask` trả mock response — nhưng log in ra cả API key và `/health` 404.
**Kết luận: chạy được ≠ production-ready.**

### Exercise 1.3 — Bảng so sánh basic vs advanced

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| Config | Hardcode | Env vars (`config.py` + `.env`, fail-fast validate) | Đổi config không sửa code; secrets không vào Git; mỗi môi trường một bộ config |
| Health check | ❌ (404) | ✅ `/health`, `/ready`, `/metrics` | Platform tự restart khi chết; LB chỉ route vào instance sẵn sàng |
| Logging | `print()`, lộ secret | JSON structured, không log secret | Parse được bởi Datadog/Loki; an toàn; lọc theo level |
| Shutdown | Đột ngột | Graceful (lifespan + SIGTERM handler) | Request đang chạy hoàn thành trước khi tắt — user không nhận lỗi |
| Binding | `localhost:8000` cứng | `0.0.0.0` + `PORT` từ env | Chạy được trong container; port do platform cấp |

### Checkpoint 1 ✅
- Hardcode secrets nguy hiểm vì: lộ vĩnh viễn trong git history, rotate phải deploy lại
- Env vars: đọc qua `os.getenv()` / pydantic-settings, file `.env` nằm trong `.gitignore`
- Health check: tín hiệu cho platform restart (liveness) và LB route traffic (readiness)
- Graceful shutdown: bắt SIGTERM → ngừng nhận request mới → chờ in-flight → thoát

---

## Part 2: Docker Containerization

### Exercise 2.1 — Câu hỏi Dockerfile cơ bản

1. **Base image:** `python:3.11` (full, ~1GB)
2. **Working directory:** `/app`
3. **COPY requirements.txt trước vì:** layer cache — code đổi thường xuyên, deps ít đổi;
   tách riêng thì sửa code không phải `pip install` lại
4. **CMD vs ENTRYPOINT:** CMD là lệnh mặc định, bị thay thế hoàn toàn khi
   `docker run image <lệnh>`; ENTRYPOINT cố định executable, args được nối thêm vào

### Exercise 2.2 — Build & run

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run -p 8003:8000 my-agent:develop
```

Kết quả: `/health` → `{"status":"ok","container":true}`. **Image size: 1.15GB**

### Exercise 2.3 — Multi-stage build

- **Stage 1 (builder):** cài gcc/libpq-dev, `pip install --user` deps vào `/root/.local`
- **Stage 2 (runtime):** từ `python:3.11-slim` sạch, chỉ COPY site-packages + code;
  non-root user `appuser`; HEALTHCHECK
- **Nhỏ hơn vì:** bỏ build tools + apt cache, base slim

**Kết quả đo thật: 1.15GB → 160MB (~7 lần).** Verify non-root: `docker exec ... whoami` → `appuser`

### Exercise 2.4 — Docker Compose stack

Architecture:
```
Client → Nginx(:80) → agent(:8000, network internal) → Redis(:6379) + Qdrant(:6333)
```
Services giao tiếp qua bridge network `internal` bằng **DNS theo tên service**
(`redis://redis:6379`, `http://qdrant:6333`); `depends_on + service_healthy` đảm bảo
thứ tự khởi động; chỉ Nginx expose port ra ngoài.

**⚠️ 3 lỗi repo phải sửa mới chạy được:**
1. `02-docker/production/requirements.txt` không tồn tại dù Dockerfile COPY → tạo mới
2. Compose `context: .` nhưng Dockerfile COPY đường dẫn từ project root → sửa `context: ../..`
3. Healthcheck Qdrant dùng `curl` nhưng image không có curl → agent không bao giờ start.
   Sửa: `test: ["CMD", "bash", "-c", ":> /dev/tcp/127.0.0.1/6333"]`

### Checkpoint 2 ✅ — debug bằng `docker logs`, `docker exec -it <id> sh`, `docker inspect`

---

## Part 3: Cloud Deployment

### Exercise 3.1 — Deploy Railway ✅ (deploy thật)

```bash
npm i -g @railway/cli
railway login                      # xác thực qua browser
railway link --project <project>   # hoặc railway init
railway add --database redis       # Redis managed
railway add --service my-production-agent \
  --variables "ENVIRONMENT=production" \
  --variables "AGENT_API_KEY=<secret>" \
  --variables 'REDIS_URL=${{Redis.REDIS_URL}}'
railway up --service my-production-agent
railway domain
```

**Public URL hoạt động:** https://my-production-agent-production.up.railway.app
- `/health` → 200 · `/ask` không key → 401 · có key → 200 · request 11/phút → 429

### Exercise 3.2 — So sánh `railway.toml` vs `render.yaml`

| | `railway.toml` | `render.yaml` |
|---|---|---|
| Triết lý | Convention over configuration | Infrastructure as Code đầy đủ |
| Nội dung | Chỉ build (builder, dockerfile) + deploy (healthcheck, restart policy) | Cả services phụ (Redis), region, plan, env vars |
| Secrets | Set ngoài qua CLI/dashboard | Khai báo trong file: `sync: false` (nhập tay), `generateValue: true` (tự sinh), `fromService` (reference) |
| Deploy | `railway up` từ máy | Auto-deploy khi push GitHub (Blueprint) |

### Exercise 3.3 — GCP Cloud Run (optional, đọc hiểu)

- `cloudbuild.yaml`: pipeline 4 bước **test → build (có `--cache-from` layer cache) →
  push registry → deploy**; secrets từ Secret Manager (`--set-secrets`)
- `service.yaml`: Knative spec — autoscaling `minScale: 1` (tránh cold start) /
  `maxScale: 10`, `containerConcurrency: 80`, livenessProbe `/health` + startupProbe `/ready`

### Câu hỏi thảo luận

1. **Serverless (Lambda) không phải lúc nào cũng tốt cho AI agent:** timeout 15 phút
   (API Gateway 29s) không đủ cho agent loop/LLM dài; streaming kém tự nhiên; cold start
   nặng với deps AI; mỗi invocation mở connection riêng tới DB/Redis (nghẽn khi scale);
   tính tiền theo thời gian chạy mà agent chủ yếu *ngồi chờ* LLM API (I/O wait) —
   trả tiền compute cho thời gian chờ.
2. **Cold start:** độ trễ khởi tạo instance mới từ 0 (pull image → start runtime →
   import deps → connect). Với AI app có thể vài giây đến vài chục giây. UX: user đầu
   tiên nhìn spinner rất lâu → cảm giác app chết; độ trễ không dự đoán được → mất niềm
   tin. Giảm bằng: min instances ≥1, image nhỏ (multi-stage!), lazy-load + `/ready`.
3. **Khi nào Railway → Cloud Run:** có users trả tiền/cần SLA; traffic biến động mạnh
   (cần autoscale 0→N theo concurrency); cần IAM/VPC/Secret Manager/audit; cần canary +
   traffic splitting; chi phí ở volume lớn. App đã 12-factor + Docker nên chuyển
   platform không phải sửa code.

### Checkpoint 3 ✅ — public URL sống, env vars trên cloud, logs qua `railway logs`

---

## Part 4: API Security

### Exercise 4.1 — API key authentication

- Key check trong dependency `verify_api_key()` — so sánh header `X-API-Key` với env
  `AGENT_API_KEY`, inject qua `Depends` vào endpoint cần bảo vệ
- Sai key → **403**, thiếu key → **401** (đã test cả 3 case: 401/403/200)
- **Rotate key:** đổi env var + restart — không sửa code, không re-deploy image

### Exercise 4.2 — JWT authentication

Flow (đã chạy thật — lưu ý credentials đúng là `student/demo123`, không phải `admin/secret`):
```bash
# 1. Đổi credentials lấy token (HS256, exp 60 phút, payload: sub + role)
curl -X POST localhost:8000/auth/token -d '{"username":"student","password":"demo123"}'
# 2. Gửi kèm token
curl -H "Authorization: Bearer $TOKEN" -X POST localhost:8000/ask -d '{"question":"..."}'
```
Không token → 401; token hết hạn → 401; token sai → 403; role-based: teacher (admin)
được limit cao hơn + truy cập `/admin/stats`.

### Exercise 4.3 — Rate limiting

- **Algorithm: Sliding Window Counter** — mỗi user 1 deque timestamps; mỗi request loại
  timestamps cũ hơn 60s rồi đếm; đủ limit → 429
- **Limit: 10 req/phút** (user), kèm headers `X-RateLimit-*` + `Retry-After`
- **Bypass cho admin:** chọn limiter theo role — admin dùng instance riêng 100 req/phút

Kết quả test: gọi 12 lần liên tục → request 1–10 trả 200, **request 11–12 trả 429**.

### Exercise 4.4 — Cost guard (Redis, budget theo tháng)

```python
from datetime import datetime, timezone
import redis

r = redis.Redis()

def check_budget(user_id: str, estimated_cost: float) -> bool:
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"        # tự "reset" khi sang tháng mới
    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:            # $10/tháng
        return False
    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)                # TTL 32 ngày — dọn key tháng cũ
    return True
```

Bản production hoàn chỉnh (raise 402, tách check/record, `/usage` endpoint) đã
implement trong `my-production-agent/app/cost_guard.py` và test thật: set chi tiêu
vượt $10 trong Redis → request bị chặn **402 Payment Required**.

**⚠️ Lỗi repo phải sửa:** `04-api-gateway/production/app.py` gọi
`response.headers.pop("server", None)` — Starlette `MutableHeaders` không có `.pop()`
→ mọi request 500. Sửa: `if "server" in response.headers: del response.headers["server"]`

### Checkpoint 4 ✅

---

## Part 5: Scaling & Reliability

### Exercise 5.1 — Health + readiness checks

```python
@app.get("/health")
def health():
    """Liveness — process còn sống. Chết → platform restart."""
    return {"status": "ok", "uptime_seconds": round(time.time() - START_TIME, 1)}

@app.get("/ready")
def ready():
    """Readiness — sẵn sàng nhận traffic chưa. 503 → LB không route vào."""
    try:
        r.ping()                                  # check dependencies (Redis/DB)
        return {"ready": True}
    except Exception:
        return JSONResponse(status_code=503, content={"ready": False})
```
Khác biệt cốt lõi: **health** trả lời "có cần restart không", **ready** trả lời
"có nên route traffic vào không" — instance đang khởi động thì sống nhưng chưa ready.

### Exercise 5.2 — Graceful shutdown

```python
import signal

_prev = signal.getsignal(signal.SIGTERM)

def handle_sigterm(signum, frame):
    # 1. log; 2. chuyển cho uvicorn handler → ngừng nhận request mới,
    # 3. lifespan shutdown chờ in-flight requests (timeout 30s), 4. exit 0
    logger.info("SIGTERM received")
    if callable(_prev):
        _prev(signum, frame)

signal.signal(signal.SIGTERM, handle_sigterm)
```

Kết quả test: gửi SIGTERM → log "Graceful shutdown initiated… Shutdown complete" →
process thoát sạch (exit 0).

**2 cái bẫy thực tế đã gặp và fix (đáng nhớ hơn cả đáp án):**
1. Docker CMD `sh -c "uvicorn ..."` → `sh` là PID 1, **không forward SIGTERM** →
   container bị SIGKILL sau timeout (exit 137). Fix: `sh -c "exec uvicorn ..."`
2. `signal.signal(SIGTERM, handler)` **đè mất handler của uvicorn** → không shutdown.
   Fix: lưu handler cũ và chain lại (như code trên).

### Exercise 5.3 — Stateless design

State (session, conversation history) lưu **Redis** với TTL, không lưu memory:
```python
# ❌ conversation_history = {}              # mất khi restart, sai khi scale
# ✅
history = r.lrange(f"history:{session_id}", 0, -1)   # instance nào đọc cũng được
r.rpush(f"history:{session_id}", json.dumps(msg)); r.expire(key, 3600)
```
Lý do: khi scale N instances, mỗi instance có memory riêng — request lượt 2 rơi vào
instance khác là mất context. Redis là single source of truth chung.

### Exercise 5.4 — Load balancing

```bash
docker compose up -d --build --scale agent=3
```
Kết quả test thật (field `served_by` trong response):
```
turn=2 instance-fce28e | turn=3 instance-5c7ce5 | turn=4 instance-b0263e
turn=5 instance-fce28e | turn=6 instance-5c7ce5 | turn=7 instance-b0263e
```
Nginx round-robin qua DNS `agent` (Docker DNS resolver `127.0.0.11`);
`proxy_next_upstream` tự chuyển sang instance khác khi 1 instance lỗi.

**⚠️ 2 lỗi repo phải sửa:** compose trỏ `05-scaling-reliability/advanced/Dockerfile`
không tồn tại (đúng là `production/` và phải tự viết Dockerfile + requirements.txt);
`app.py` chạy `uvicorn.run(app, reload=True)` với app object → exit 1, container
restart loop → đổi CMD thành `uvicorn app:app` trực tiếp.

### Exercise 5.5 — Test stateless

- `docker kill` 1 instance giữa cuộc hội thoại → 3 requests sau vẫn 200,
  **history 18 messages không mất** (Nginx failover + state trong Redis)
- Script chính thức: `python test_stateless.py` →
  `✅ Session history preserved across all instances via Redis!`

### Checkpoint 5 ✅

---

## Phụ lục: Tổng hợp lỗi có sẵn trong repo đã sửa

| # | Vị trí | Lỗi | Fix |
|---|---|---|---|
| 1 | `02-docker/production/` | Thiếu `requirements.txt` mà Dockerfile COPY | Tạo mới |
| 2 | `02-docker/production/docker-compose.yml` | Build context `.` sai với đường dẫn COPY | `context: ../..` |
| 3 | `02-docker/production/docker-compose.yml` | Healthcheck Qdrant dùng curl (image không có) | TCP check bằng bash `/dev/tcp` |
| 4 | `04-api-gateway/production/app.py` | `headers.pop()` không tồn tại → 500 mọi request | `del response.headers["server"]` |
| 5 | `05-scaling-reliability/production/` | Thiếu Dockerfile, compose trỏ thư mục `advanced/` không tồn tại | Viết Dockerfile + sửa path |
| 6 | `05-scaling-reliability/production/app.py` | `reload=True` với app object → restart loop | CMD `uvicorn app:app` |

## Kết quả cuối

- **Part 6:** `my-production-agent/` — `check_production_ready.py` đạt **20/20 (100%)**
- **Production:** https://my-production-agent-production.up.railway.app (Railway + Redis managed)
- **Bonus CI/CD:** GitHub Actions — lint (ruff) + 24 unit tests (coverage 94%, gate 80%) →
  auto-deploy Railway + smoke test. Đã demo cả 2 chiều: lint đỏ chặn deploy, fix xong tự lên production.
