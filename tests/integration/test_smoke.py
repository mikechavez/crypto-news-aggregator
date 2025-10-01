from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

LOG_FILE = Path("logs/app.log")


@pytest.mark.integration
def test_healthcheck(server_process):
    assert server_process["health_url"].endswith("/api/v1/health")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_price_query_succeeds(server_process, http_client):
    base_url = server_process["base_url"]

    payload = {
        "model": "crypto-insight-agent",
        "messages": [
            {"role": "user", "content": "What is the current price of BTC and ETH?"}
        ],
        "stream": False,
    }

    headers = {"X-API-Key": "testapikey123"}

    resp = await http_client.post(
        f"{base_url}/v1/chat/completions", json=payload, headers=headers, timeout=30
    )

    assert (
        resp.status_code == 200
    ), f"Unexpected status: {resp.status_code}, body: {resp.text}"

    data = resp.json()
    assert isinstance(data, dict)
    assert (
        "choices" in data and isinstance(data["choices"], list) and data["choices"]
    ), "choices missing or empty"

    content = data["choices"][0].get("message", {}).get("content", "")
    assert (
        isinstance(content, str) and content.strip()
    ), "Empty content returned for price query"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sentiment_query_handled(server_process, http_client):
    base_url = server_process["base_url"]

    payload = {
        "model": "crypto-insight-agent",
        "messages": [
            {"role": "user", "content": "What is the market sentiment for SOL?"}
        ],
        "stream": False,
    }

    headers = {"X-API-Key": "testapikey123"}

    resp = await http_client.post(
        f"{base_url}/v1/chat/completions", json=payload, headers=headers, timeout=30
    )

    # Should not 5xx; either 200 with content or a well-formed 4xx with JSON body
    assert (
        resp.status_code < 500
    ), f"Sentiment query returned 5xx: {resp.status_code}, body: {resp.text}"

    # If 200, validate non-empty content
    if resp.status_code == 200:
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        assert (
            isinstance(content, str) and content.strip()
        ), "Empty content returned for sentiment query"
    else:
        # For non-200, ensure it's JSON and informative
        try:
            _ = resp.json()
        except Exception as e:
            pytest.fail(
                f"Non-200 sentiment response is not JSON: {e}; body={resp.text}"
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_logs_have_activity_marker(server_process):
    # Optional, non-flaky check: if log file exists, ensure it has activity
    # We do not fail the build if logs are missing, as log routing can vary in CI.
    await asyncio.sleep(1.0)
    if not LOG_FILE.exists():
        pytest.skip("logs/app.log not present in this environment")

    text = LOG_FILE.read_text(encoding="utf-8", errors="ignore")
    # Look for at least one of the expected markers
    markers = [
        "Logging configured",
        "Starting application",
        "Received chat completion request",
        "Classified intent",
    ]
    assert any(
        m in text for m in markers
    ), "Expected log markers not found in logs/app.log"
