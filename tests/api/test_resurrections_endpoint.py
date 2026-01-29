"""
Tests for the resurrections API endpoint.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient


def test_get_resurrected_narratives_empty(client):
    """Test resurrections endpoint returns empty list when no resurrected narratives exist."""
    response = client.get("/api/v1/narratives/resurrections")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_resurrected_narratives_with_limit(client):
    """Test resurrections endpoint respects limit parameter."""
    response = client.get("/api/v1/narratives/resurrections?limit=5")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5


def test_get_resurrected_narratives_with_days(client):
    """Test resurrections endpoint respects days parameter."""
    response = client.get("/api/v1/narratives/resurrections?days=14")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_resurrected_narratives_invalid_limit(client):
    """Test resurrections endpoint rejects invalid limit."""
    response = client.get("/api/v1/narratives/resurrections?limit=150")
    
    assert response.status_code == 422  # Validation error


def test_get_resurrected_narratives_invalid_days(client):
    """Test resurrections endpoint rejects invalid days."""
    response = client.get("/api/v1/narratives/resurrections?days=50")
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_resurrected_narrative_structure(client, mongo_db):
    """Test that resurrected narratives have correct structure including resurrection metrics."""
    # Insert a test resurrected narrative
    narratives_collection = mongo_db.narratives
    
    now = datetime.now(timezone.utc)
    reawakened_from = now - timedelta(days=2)
    
    test_narrative = {
        "theme": "test_resurrection",
        "title": "Test Resurrected Narrative",
        "summary": "A narrative that came back from dormancy",
        "entities": ["Bitcoin", "ETF"],
        "article_ids": [],
        "article_count": 10,
        "mention_velocity": 2.5,
        "lifecycle": "rising",
        "lifecycle_state": "rising",
        "momentum": "growing",
        "recency_score": 0.8,
        "entity_relationships": [],
        "first_seen": now - timedelta(days=30),
        "last_updated": now,
        "days_active": 30,
        "reawakening_count": 2,
        "reawakened_from": reawakened_from,
        "resurrection_velocity": 3.2,
        "timeline_data": [],
        "peak_activity": {
            "date": now.date().isoformat(),
            "article_count": 10,
            "velocity": 2.5
        }
    }
    
    await narratives_collection.insert_one(test_narrative)
    
    # Fetch resurrected narratives
    response = client.get("/api/v1/narratives/resurrections?days=7")
    
    assert response.status_code == 200
    data = response.json()
    
    # Find our test narrative
    test_result = None
    for narrative in data:
        if narrative["theme"] == "test_resurrection":
            test_result = narrative
            break
    
    assert test_result is not None, "Test narrative not found in results"
    
    # Verify resurrection metrics are present
    assert test_result["reawakening_count"] == 2
    assert test_result["reawakened_from"] is not None
    assert test_result["resurrection_velocity"] == 3.2
    
    # Verify standard narrative fields
    assert test_result["title"] == "Test Resurrected Narrative"
    assert test_result["article_count"] == 10
    assert test_result["mention_velocity"] == 2.5
    assert "Bitcoin" in test_result["entities"]
    
    # Cleanup
    await narratives_collection.delete_one({"theme": "test_resurrection"})


@pytest.mark.asyncio
async def test_resurrected_narratives_sorted_by_reawakened_from(client, mongo_db):
    """Test that resurrected narratives are sorted by reawakened_from descending."""
    narratives_collection = mongo_db.narratives
    
    now = datetime.now(timezone.utc)
    
    # Insert multiple resurrected narratives with different reawakened_from dates
    test_narratives = [
        {
            "theme": "test_resurrection_1",
            "title": "Oldest Resurrection",
            "summary": "Resurrected 5 days ago",
            "entities": ["BTC"],
            "article_ids": [],
            "article_count": 5,
            "mention_velocity": 1.0,
            "lifecycle": "rising",
            "first_seen": now - timedelta(days=20),
            "last_updated": now,
            "reawakening_count": 1,
            "reawakened_from": now - timedelta(days=5),
            "resurrection_velocity": 1.5,
            "timeline_data": []
        },
        {
            "theme": "test_resurrection_2",
            "title": "Newest Resurrection",
            "summary": "Resurrected 1 day ago",
            "entities": ["ETH"],
            "article_ids": [],
            "article_count": 8,
            "mention_velocity": 2.0,
            "lifecycle": "hot",
            "first_seen": now - timedelta(days=15),
            "last_updated": now,
            "reawakening_count": 1,
            "reawakened_from": now - timedelta(days=1),
            "resurrection_velocity": 3.0,
            "timeline_data": []
        },
        {
            "theme": "test_resurrection_3",
            "title": "Middle Resurrection",
            "summary": "Resurrected 3 days ago",
            "entities": ["SOL"],
            "article_ids": [],
            "article_count": 6,
            "mention_velocity": 1.5,
            "lifecycle": "rising",
            "first_seen": now - timedelta(days=25),
            "last_updated": now,
            "reawakening_count": 2,
            "reawakened_from": now - timedelta(days=3),
            "resurrection_velocity": 2.0,
            "timeline_data": []
        }
    ]
    
    await narratives_collection.insert_many(test_narratives)
    
    # Fetch resurrected narratives
    response = client.get("/api/v1/narratives/resurrections?days=7")
    
    assert response.status_code == 200
    data = response.json()
    
    # Filter to only our test narratives
    test_results = [n for n in data if n["theme"].startswith("test_resurrection_")]
    
    assert len(test_results) == 3, "Should have 3 test narratives"
    
    # Verify they are sorted by reawakened_from descending (newest first)
    assert test_results[0]["title"] == "Newest Resurrection"
    assert test_results[1]["title"] == "Middle Resurrection"
    assert test_results[2]["title"] == "Oldest Resurrection"
    
    # Cleanup
    await narratives_collection.delete_many({"theme": {"$regex": "^test_resurrection_"}})
