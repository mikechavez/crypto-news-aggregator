"""Integration-level fixtures for running the FastAPI app in a real uvicorn subprocess.

These fixtures intentionally start the app as a separate process to validate that
it starts correctly and serves real HTTP requests. They are kept local to the
`tests/integration/` package to avoid affecting faster unit tests.
"""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import httpx

HOST = "127.0.0.1"


def _find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((HOST, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def _wait_for_health(
    urls: list[str] | str, proc: subprocess.Popen | None = None, timeout: float = 12.0
) -> None:
    if isinstance(urls, str):
        probe_urls = [urls]
    else:
        probe_urls = urls
    start = time.time()
    last_log: dict[str, float] = {}
    with httpx.Client() as client:
        while time.time() - start < timeout:
            # If the process exited early, fail fast with its output
            if proc is not None and proc.poll() is not None:
                out = ""
                try:
                    if proc.stdout:
                        out = proc.stdout.read() or ""
                except Exception:
                    pass
                raise TimeoutError(
                    f"Server process exited early with code {proc.returncode}. STDOUT tail:\n{out[-2000:]}"
                )
            for url in probe_urls:
                try:
                    r = client.get(url, timeout=2)
                    if r.status_code == 200:
                        return
                    now = time.time()
                    if last_log.get(url, 0) < now - 1.0:
                        # Log at most once per second per URL
                        body = r.text if hasattr(r, "text") else ""
                        print(f"[probe] {url} -> {r.status_code}: {body[:160]}")
                        last_log[url] = now
                except Exception:
                    pass
            time.sleep(0.25)
    # If we reach here, include a tail of stdout for debugging
    tail = ""
    try:
        if proc and proc.stdout:
            try:
                proc.poll()
            except Exception:
                pass
            out = proc.stdout.read()
            if out:
                tail = out[-2000:]
    except Exception:
        pass
    raise TimeoutError(f"Server did not become healthy in time. STDOUT tail:\n{tail}")


@pytest.fixture(scope="function")
def server_process(tmp_path: Path) -> Generator[dict, None, None]:
    """Start the FastAPI app with uvicorn in a subprocess on a free port.

    Yields a dict with keys: proc, base_url, port, health_url.
    Ensures process is terminated at the end of the test.
    """
    port = _find_free_port()
    base_url = f"http://{HOST}:{port}"
    health_url = f"{base_url}/api/v1/health"
    probe_urls = [
        f"{base_url}/openapi.json",
        f"{base_url}/docs",
        health_url,
    ]

    # Ensure the app can be imported by uvicorn even if the package isn't installed
    repo_root = Path(__file__).resolve().parents[2]
    src_dir = repo_root / "src"

    env = os.environ.copy()
    # Disable DEBUG/TESTING to avoid importing debug-only endpoints that may rely on unavailable test-only symbols
    env["DEBUG"] = "false"
    env["TESTING"] = "true"
    env.setdefault("ENABLE_DB_SYNC", "false")
    env.setdefault("FORCE_SQLITE", "true")
    # Ensure default API prefix so health URL is predictable
    env.setdefault("API_V1_STR", "/api/v1")
    # Disable test-only endpoints to avoid import issues
    env.setdefault("ENABLE_TEST_ENDPOINTS", "false")
    # Avoid slow Mongo initialization during startup; the app handles degraded mode
    env["MONGODB_URI"] = ""
    env.setdefault("MONGODB_NAME", "test_crypto_news_aggregator")
    # Provide a test API key consistent with the rest of the suite
    env.setdefault("API_KEYS", "testapikey123")
    # Ensure the package can be resolved
    env["PYTHONPATH"] = f"{src_dir}:{env.get('PYTHONPATH', '')}"

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "crypto_news_aggregator.main:app",
        "--host",
        HOST,
        "--port",
        str(port),
        "--log-level",
        "debug",
    ]

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        # Wait synchronously for server readiness using multiple generic probes
        _wait_for_health(probe_urls, proc)
        yield {
            "proc": proc,
            "base_url": base_url,
            "port": port,
            "health_url": health_url,
        }
    finally:
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception:
                pass


@pytest.fixture(scope="function")
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient() as client:
        yield client
