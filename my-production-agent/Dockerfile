# ── STAGE 1: Builder — cài dependencies ─────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── STAGE 2: Runtime — chỉ chứa những gì cần để chạy ────────
FROM python:3.11-slim AS runtime

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local

# Gateway production + Legal Multi-Agent System
COPY app/ ./app/
COPY common/ ./common/
COPY registry/ ./registry/
COPY customer_agent/ ./customer_agent/
COPY law_agent/ ./law_agent/
COPY tax_agent/ ./tax_agent/
COPY compliance_agent/ ./compliance_agent/
COPY run_all.py .

RUN chown -R appuser:appuser /app
USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://localhost:{os.getenv(\"PORT\",\"8000\")}/health')" || exit 1

# exec → python (supervisor) là PID 1, nhận SIGTERM → graceful shutdown
CMD ["sh", "-c", "exec python run_all.py"]
