"""Smoke tests to validate core application functionality."""
from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_worker_starts_successfully(monkeypatch: pytest.MonkeyPatch) -> None:
    """Import and initialize the background worker without raising exceptions."""
    import crypto_news_aggregator.worker as worker

    dummy_settings = SimpleNamespace(TESTING=True)
    monkeypatch.setattr(worker, "get_settings", lambda: dummy_settings)

    state = {"initialized": False}

    async def fake_initialize_mongodb() -> None:
        state["initialized"] = True

    monkeypatch.setattr(worker, "initialize_mongodb", fake_initialize_mongodb)

    await worker.main()

    assert state["initialized"], "Worker did not attempt MongoDB initialization"


def test_api_health_check(client) -> None:
    """Verify the API health endpoint responds with HTTP 200."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_mongodb_connection() -> None:
    """Ensure MongoDB insert and read operations succeed."""
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=1500,
        connectTimeoutMS=1500,
        socketTimeoutMS=2000,
    )

    db_name = "smoke_test_core"
    collection_name = "smoke_tests"

    try:
        await client.admin.command("ping")
        db = client[db_name]
        collection = db[collection_name]

        await collection.delete_many({})

        document = {"_id": "smoke-check", "status": "ok"}
        await collection.insert_one(document)
        stored = await collection.find_one({"_id": "smoke-check"})

        assert stored is not None, "Document was not written to MongoDB"
        assert stored.get("status") == "ok"
    finally:
        await client.drop_database(db_name)
        client.close()
