# Build từ project root:
#   docker build -f 05-scaling-reliability/production/Dockerfile -t agent-stateless .
FROM python:3.11-slim

WORKDIR /app

COPY 05-scaling-reliability/production/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY 05-scaling-reliability/production/app.py .
COPY utils/mock_llm.py utils/

EXPOSE 8000

# app.py __main__ bật reload=True (chỉ dành cho dev) — chạy uvicorn trực tiếp
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
