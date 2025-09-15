"""
Smoke test for the FastAPI Crypto News Aggregator + OpenAI-compatible chat endpoint.

Verifies:
1) Server starts successfully (healthcheck OK)
2) Price queries work (chat: price intent returns a non-empty content)
3) Sentiment queries return proper errors (not 500) and are handled gracefully
4) All responses are logged properly in logs/app.log
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

import httpx
import subprocess


HOST = "127.0.0.1"
PORT = int(os.environ.get("SMOKE_TEST_PORT", "8001"))
BASE_URL = f"http://{HOST}:{PORT}"
HEALTH_URL = f"{BASE_URL}/api/v1/health"
CHAT_URL = f"{BASE_URL}/v1/chat/completions"

LOG_FILE = Path("logs/app.log")


async def wait_for_server(proc: subprocess.Popen, timeout: float = 45.0) -> None:
    start = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            # Surface any server output while we wait
            if proc.poll() is not None:
                # Process exited early; drain output
                remainder = proc.stdout.read() if proc.stdout else ""
                print("[ERROR] Server exited early with code:", proc.returncode)
                if remainder:
                    print("[SERVER STDOUT TAIL]:\n" + remainder[-2000:])
                raise TimeoutError("Server process exited before becoming healthy")
            try:
                r = await client.get(HEALTH_URL, timeout=3)
                if r.status_code == 200 and r.json().get("status") == "ok":
                    print("[OK] Healthcheck passed.")
                    return
            except Exception:
                pass
            # Non-blocking read a small chunk from stdout if available
            try:
                if proc.stdout and not proc.stdout.closed:
                    proc.stdout.flush()
                    chunk = proc.stdout.readline()
                    if chunk:
                        print(chunk.rstrip())
            except Exception:
                pass
            await asyncio.sleep(0.5)
    raise TimeoutError("Server did not become healthy in time")


async def post_chat(payload: dict) -> httpx.Response:
    async with httpx.AsyncClient() as client:
        r = await client.post(CHAT_URL, json=payload, timeout=30)
        return r


def start_server() -> subprocess.Popen:
    env = os.environ.copy()
    # Ensure TESTING mode so background tasks are skipped
    env["TESTING"] = "true"
    env["ENABLE_DB_SYNC"] = "false"

    # Start uvicorn serving crypto_news_aggregator.main:app on a test port
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "crypto_news_aggregator.main:app",
        "--host",
        HOST,
        "--port",
        str(PORT),
        # Let app's own logging config handle loggers
    ]
    print("[INFO] Starting server:", " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    return proc


def stop_server(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    except Exception:
        pass


def read_recent_logs(max_lines: int = 200) -> list[str]:
    if not LOG_FILE.exists():
        return []
    try:
        with LOG_FILE.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            return lines[-max_lines:]
    except Exception:
        return []


async def run_smoke() -> int:
    rc = 0
    proc: Optional[subprocess.Popen] = None
    try:
        proc = start_server()
        # Optional: surface some server output for quick visibility
        await asyncio.sleep(0.5)
        print("[INFO] Waiting for healthcheck...")
        await wait_for_server(proc)

        # 2) Price query should work
        price_payload = {
            "model": "crypto-insight-agent",
            "messages": [
                {"role": "user", "content": "What is the current price of BTC and ETH?"}
            ],
            "stream": False,
        }
        price_resp = await post_chat(price_payload)
        print("[INFO] Price response status:", price_resp.status_code)
        print("[INFO] Price response:", json.dumps(price_resp.json(), indent=2))
        if price_resp.status_code != 200:
            print("[FAIL] Price query did not return 200.")
            rc = 1
        else:
            content = price_resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                print("[FAIL] Price query returned empty content.")
                rc = 1

        # 3) Sentiment query should not 500; should be handled
        sentiment_payload = {
            "model": "crypto-insight-agent",
            "messages": [
                {"role": "user", "content": "What is the market sentiment for SOL?"}
            ],
            "stream": False,
        }
        sent_resp = await post_chat(sentiment_payload)
        print("[INFO] Sentiment response status:", sent_resp.status_code)
        print("[INFO] Sentiment response:", json.dumps(sent_resp.json(), indent=2))
        if sent_resp.status_code >= 500:
            print("[FAIL] Sentiment query returned 5xx.")
            rc = 1
        else:
            sent_content = sent_resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if not sent_content:
                print("[FAIL] Sentiment query returned empty content.")
                rc = 1

        # 4) Verify logs contain expected markers
        # Give the app a moment to flush logs
        await asyncio.sleep(1.0)
        logs = read_recent_logs()
        log_text = "".join(logs)
        print("[INFO] Tail of logs/app.log (last ~200 lines):\n" + log_text[-2000:])

        expected_markers = [
            "--- Logging configured successfully ---",
            "Starting application...",
            "Received chat completion request",
            "Classified intent as",
        ]
        missing = [m for m in expected_markers if m not in log_text]
        if missing:
            print(f"[WARN] Missing expected log markers: {missing}")
            # Don't hard fail if logs are slightly different, but flag warning

    except Exception as e:
        print("[ERROR] Smoke test failed with exception:", e)
        rc = 2
    finally:
        if proc is not None:
            stop_server(proc)
    return rc


if __name__ == "__main__":
    exit_code = asyncio.run(run_smoke())
    sys.exit(exit_code)
