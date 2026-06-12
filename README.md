# Day 12 — Deployment: Đưa Agent Lên Cloud

> **AICB-P1 · VinUniversity 2026**  
> Repository thực hành đi kèm bài giảng Day 12.  
> Mỗi phần có ví dụ **cơ bản** (hiểu concept) và **chuyên sâu** (production-ready).

---

## 📌 BÀI NỘP — dành cho giảng viên

> **Toàn bộ bài làm nằm trong folder [`my-production-agent/`](my-production-agent/)**
>
> Sản phẩm là **Legal Multi-Agent System của Day 9** (A2A protocol + LangGraph:
> Customer → Law → Tax + Compliance agents, Registry service discovery)
> được đóng gói và vận hành bằng toàn bộ kiến thức Day 12:
> Docker multi-stage, API key auth, rate limiting, cost guard, health/ready,
> graceful shutdown, stateless Redis, structured logging.
>
> | Hạng mục | Link / Lệnh |
> |---|---|
> | 🌐 **Live demo** (Railway) | https://my-production-agent-production.up.railway.app |
> | 📖 Chi tiết bài làm | [`my-production-agent/README.md`](my-production-agent/README.md) |
> | 📝 Đáp án Part 1→5 | [`Solution.md`](Solution.md) |
> | ⚙️ CI/CD (bonus) | [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) — lint + tests (coverage 94%) → auto-deploy Railway |
> | ✅ Validation | `cd my-production-agent && python check_production_ready.py` → 20/20 |
> | 🐳 Chạy local | `cd my-production-agent && docker compose up -d --build` → http://localhost:8088 |

---

## Cấu Trúc Project

```
day12_ha-tang-cloud_va_deployment/
├── 01-localhost-vs-production/     # Section 1: Dev ≠ Production
│   ├── develop/                      #   Agent "đúng kiểu localhost"
│   └── production/                   #   12-Factor compliant agent
│
├── 02-docker/                      # Section 2: Containerization
│   ├── develop/                      #   Dockerfile đơn giản
│   └── production/                   #   Multi-stage + Docker Compose stack
│
├── 03-cloud-deployment/            # Section 3: Cloud Options
│   ├── railway/                    #   Deploy Railway (< 5 phút)
│   ├── render/                     #   Deploy Render + render.yaml
│   └── production-cloud-run/         #   GCP Cloud Run + CI/CD
│
├── 04-api-gateway/                 # Section 4: Security
│   ├── develop/                      #   API Key authentication
│   └── production/                   #   JWT + Rate Limiting + Cost Guard
│
├── 05-scaling-reliability/         # Section 5: Scale & Reliability
│   ├── develop/                      #   Health check + graceful shutdown
│   └── production/                   #   Stateless + Redis + Nginx LB
│
├── 06-lab-complete/                # Lab 12: Production-ready agent
│   └── (full project kết hợp tất cả)
│
└── utils/                          # Mock LLM dùng chung (không cần API key)
```

---

## 🚀 Bắt Đầu Nhanh

**Muốn thử ngay?** → [QUICK_START.md](QUICK_START.md) (5 phút)

**Muốn học kỹ?** → [CODE_LAB.md](CODE_LAB.md) (3-4 giờ)

## Cách Học

| Bước | Làm gì |
|------|--------|
| 0 | **[Khuyến nghị]** Đọc [QUICK_START.md](QUICK_START.md) để thử nhanh |
| 1 | Đọc [CODE_LAB.md](CODE_LAB.md) để hiểu chi tiết |
| 2 | Chạy ví dụ **basic** trước — hiểu concept |
| 3 | So sánh với ví dụ **advanced** — thấy sự khác biệt |
| 4 | Tự làm Lab 06 từ đầu trước khi xem solution |
| 5 | Tham khảo [QUICK_REFERENCE.md](QUICK_REFERENCE.md) khi cần |
| 6 | Xem [TROUBLESHOOTING.md](TROUBLESHOOTING.md) khi gặp lỗi |

---

## Yêu Cầu

```bash
python 3.11+
docker & docker compose
```

Mỗi folder có `requirements.txt` riêng. Không cần API key thật — các ví dụ dùng **mock LLM** để chạy offline.

---

## Sections

| # | Folder | Concept chính |
|---|--------|--------------|
| 1 | `01-localhost-vs-production` | Dev/prod gap, 12-factor, secrets |
| 2 | `02-docker` | Dockerfile, multi-stage, docker-compose |
| 3 | `03-cloud-deployment` | Railway, Render, Cloud Run |
| 4 | `04-api-gateway` | Auth, rate limiting, cost protection |
| 5 | `05-scaling-reliability` | Health check, stateless, rolling deploy |
| 6 | `06-lab-complete` | **Full production agent** |

---

## 📚 Lab Materials

Chúng tôi đã chuẩn bị đầy đủ tài liệu hướng dẫn:

### Cho Sinh Viên

| Tài liệu | Mô tả | Thời gian |
|----------|-------|-----------|
| **[CODE_LAB.md](CODE_LAB.md)** | Hướng dẫn lab chi tiết từng bước | 3-4 giờ |
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | Cheat sheet các lệnh và patterns | Tra cứu |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Giải quyết lỗi thường gặp | Khi cần |

### Cho Giảng Viên

| Tài liệu | Mô tả |
|----------|-------|
| **[INSTRUCTOR_GUIDE.md](INSTRUCTOR_GUIDE.md)** | Hướng dẫn chấm điểm và đánh giá |

### Cách Sử Dụng

1. **Trước lab:** Đọc [CODE_LAB.md](CODE_LAB.md) để hiểu tổng quan
2. **Trong lab:** Làm theo từng Part, tham khảo [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. **Gặp lỗi:** Xem [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. **Sau lab:** Nộp Part 6 Final Project để chấm điểm
