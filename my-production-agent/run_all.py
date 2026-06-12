"""
Supervisor — khởi động toàn bộ Legal Multi-Agent System trong một container.

Thứ tự: Registry (:10000) → Tax (:10102) + Compliance (:10103) → Law (:10101)
        → Customer (:10100) → Gateway (app.main) trên $PORT.

Gateway chạy trong process chính (PID nhận SIGTERM → uvicorn graceful shutdown),
các agent là child processes và bị terminate khi gateway tắt.
"""
import atexit
import os
import signal
import subprocess
import sys
import time

import uvicorn

SERVICES = [
    ("registry", 2.0),
    ("tax_agent", 0.0),
    ("compliance_agent", 3.0),
    ("law_agent", 3.0),
    ("customer_agent", 3.0),
]

children: list[subprocess.Popen] = []


def _shutdown_children(*_args):
    for proc in children:
        if proc.poll() is None:
            proc.terminate()
    deadline = time.time() + 10
    for proc in children:
        remaining = max(0.1, deadline - time.time())
        try:
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    env = os.environ.copy()
    env.setdefault("REGISTRY_URL", "http://localhost:10000")

    for module, wait_after in SERVICES:
        print(f"[supervisor] starting {module} ...", flush=True)
        proc = subprocess.Popen([sys.executable, "-m", module], env=env)
        children.append(proc)
        if wait_after:
            time.sleep(wait_after)

    atexit.register(_shutdown_children)
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))  # → atexit dọn children

    port = int(os.getenv("PORT", "8000"))
    print(f"[supervisor] starting gateway on :{port}", flush=True)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port,
                timeout_graceful_shutdown=30)


if __name__ == "__main__":
    main()
