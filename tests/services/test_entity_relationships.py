"""
Tests for entity co-occurrence relationship tracking in narratives.

Tests the extraction and storage of entity relationships based on
co-occurrence patterns in article clusters.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from crypto_news_aggregator.services.narrative_themes import (
    generate_narrative_from_cluster
)
from crypto_news_aggregator.db.operations.narratives import upsert_narrative


@pytest.fixture
def sample_cluster_with_relationships():
    """Sample article cluster with overlapping actors for relationship testing."""
    return [
        {
            "_id": "article1",
            "title": "Bitcoin and Ethereum Rally",
            "narrative_summary": "BTC and ETH prices surge",
            "actors": ["Bitcoin", "Ethereum", "Coinbase"],
            "tensions": ["price_volatility"],
            "nucleus_entity": "Bitcoin",
            "published_at": datetime.now(timezone.utc)
        },
        {
            "_id": "article2",
            "title": "Bitcoin Adoption Grows",
            "narrative_summary": "Major institutions adopt BTC",
            "actors": ["Bitcoin", "MicroStrategy", "Coinbase"],
            "tensions": ["institutional_adoption"],
            "nucleus_entity": "Bitcoin",
            "published_at": datetime.now(timezone.utc)
        },
        {
            "_id": "article3",
            "title": "Coinbase Lists New Assets",
            "narrative_summary": "Exchange expands offerings",
            "actors": ["Coinbase", "Bitcoin", "Ethereum"],
            "tensions": ["market_expansion"],
            "nucleus_entity": "Bitcoin",
            "published_at": datetime.now(timezone.utc)
        },
        {
            "_id": "article4",
            "title": "MicroStrategy Buys More Bitcoin",
            "narrative_summary": "Company increases BTC holdings",
            "actors": ["MicroStrategy", "Bitcoin"],
            "tensions": ["institutional_adoption"],
            "nucleus_entity": "Bitcoin",
            "published_at": datetime.now(timezone.utc)
        }
    ]


@pytest.fixture
def sample_cluster_single_actors():
    """Sample cluster where articles have only single actors (no relationships)."""
    return [
        {
            "_id": "article1",
            "title": "Bitcoin News",
            "narrative_summary": "BTC update",
            "actors": ["Bitcoin"],
            "tensions": ["price_volatility"],
            "nucleus_entity": "Bitcoin",
            "published_at": datetime.now(timezone.utc)
        },
        {
            "_id": "article2",
            "title": "Ethereum News",
            "narrative_summary": "ETH update",
            "actors": ["Ethereum"],
            "tensions": ["network_upgrade"],
            "nucleus_entity": "Ethereum",
            "published_at": datetime.now(timezone.utc)
        }
    ]


@pytest.mark.asyncio
async def test_generate_narrative_extracts_relationships(sample_cluster_with_relationships):
    """Test that generate_narrative_from_cluster extracts entity relationships."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        # Mock LLM response
        mock_client = MagicMock()
        mock_client._get_completion.return_value = '{"title": "Bitcoin Ecosystem Growth", "summary": "Bitcoin adoption accelerates."}'
        mock_llm.return_value = mock_client
        
        # Generate narrative
        narrative = await generate_narrative_from_cluster(sample_cluster_with_relationships)
        
        # Verify narrative was generated
        assert narrative is not None
        assert "entity_relationships" in narrative
        
        # Verify relationships were extracted
        relationships = narrative["entity_relationships"]
        assert isinstance(relationships, list)
        assert len(relationships) > 0
        
        # Verify relationship structure
        for rel in relationships:
            assert "a" in rel
            assert "b" in rel
            assert "weight" in rel
            assert isinstance(rel["weight"], int)
            assert rel["weight"] > 0
        
        # Verify most common relationships are captured
        # Bitcoin-Coinbase appears in 3 articles
        # Bitcoin-Ethereum appears in 2 articles
        # Bitcoin-MicroStrategy appears in 2 articles
        relationship_pairs = [(rel["a"], rel["b"]) for rel in relationships]
        
        # Check that Bitcoin-Coinbase is in top relationships (highest co-occurrence)
        bitcoin_coinbase = any(
            (a == "Bitcoin" and b == "Coinbase") or (a == "Coinbase" and b == "Bitcoin")
            for a, b in relationship_pairs
        )
        assert bitcoin_coinbase, "Bitcoin-Coinbase relationship should be detected"


@pytest.mark.asyncio
async def test_generate_narrative_no_relationships_single_actors(sample_cluster_single_actors):
    """Test that clusters with single actors per article have empty relationships."""
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        # Mock LLM response
        mock_client = MagicMock()
        mock_client._get_completion.return_value = '{"title": "Crypto Market Update", "summary": "Market activity continues."}'
        mock_llm.return_value = mock_client
        
        # Generate narrative
        narrative = await generate_narrative_from_cluster(sample_cluster_single_actors)
        
        # Verify narrative was generated
        assert narrative is not None
        assert "entity_relationships" in narrative
        
        # Verify no relationships (articles have only 1 actor each)
        relationships = narrative["entity_relationships"]
        assert isinstance(relationships, list)
        assert len(relationships) == 0


@pytest.mark.asyncio
async def test_generate_narrative_limits_top_5_relationships():
    """Test that only top 5 relationships by weight are stored."""
    # Create cluster with many different actor pairs
    cluster = []
    actors_sets = [
        ["A", "B", "C"],
        ["A", "B", "D"],
        ["A", "B", "E"],
        ["A", "B", "F"],
        ["A", "C", "G"],
        ["A", "D", "H"],
        ["A", "E", "I"],
        ["A", "F", "J"],
    ]
    
    for i, actors in enumerate(actors_sets):
        cluster.append({
            "_id": f"article{i}",
            "title": f"Article {i}",
            "narrative_summary": f"Summary {i}",
            "actors": actors,
            "tensions": ["test"],
            "nucleus_entity": "A",
            "published_at": datetime.now(timezone.utc)
        })
    
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        # Mock LLM response
        mock_client = MagicMock()
        mock_client._get_completion.return_value = '{"title": "Test Narrative", "summary": "Test summary."}'
        mock_llm.return_value = mock_client
        
        # Generate narrative
        narrative = await generate_narrative_from_cluster(cluster)
        
        # Verify only top 5 relationships are stored
        assert narrative is not None
        relationships = narrative["entity_relationships"]
        assert len(relationships) <= 5


@pytest.mark.asyncio
async def test_generate_narrative_relationship_weights():
    """Test that relationship weights correctly reflect co-occurrence counts."""
    cluster = [
        {
            "_id": "article1",
            "title": "Article 1",
            "narrative_summary": "Summary 1",
            "actors": ["Bitcoin", "Ethereum"],  # Pair appears once
            "tensions": ["test"],
            "nucleus_entity": "Bitcoin",
            "published_at": datetime.now(timezone.utc)
        },
        {
            "_id": "article2",
            "title": "Article 2",
            "narrative_summary": "Summary 2",
            "actors": ["Bitcoin", "Ethereum"],  # Pair appears twice
            "tensions": ["test"],
            "nucleus_entity": "Bitcoin",
            "published_at": datetime.now(timezone.utc)
        },
        {
            "_id": "article3",
            "title": "Article 3",
            "narrative_summary": "Summary 3",
            "actors": ["Bitcoin", "Ethereum"],  # Pair appears three times
            "tensions": ["test"],
            "nucleus_entity": "Bitcoin",
            "published_at": datetime.now(timezone.utc)
        },
    ]
    
    with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
        # Mock LLM response
        mock_client = MagicMock()
        mock_client._get_completion.return_value = '{"title": "BTC-ETH Narrative", "summary": "Bitcoin and Ethereum news."}'
        mock_llm.return_value = mock_client
        
        # Generate narrative
        narrative = await generate_narrative_from_cluster(cluster)
        
        # Verify relationship weight
        assert narrative is not None
        relationships = narrative["entity_relationships"]
        assert len(relationships) == 1  # Only one unique pair
        
        rel = relationships[0]
        assert set([rel["a"], rel["b"]]) == {"Bitcoin", "Ethereum"}
        assert rel["weight"] == 3  # Appears in all 3 articles


@pytest.mark.asyncio
async def test_upsert_narrative_stores_entity_relationships():
    """Test that upsert_narrative correctly stores entity relationships in database."""
    with patch("crypto_news_aggregator.db.operations.narratives.mongo_manager") as mock_mongo:
        # Mock database
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.narratives = mock_collection
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Mock find_one to return None (new narrative)
        mock_collection.find_one = AsyncMock(return_value=None)
        
        # Mock insert_one
        mock_result = MagicMock()
        mock_result.inserted_id = "narrative123"
        mock_collection.insert_one = AsyncMock(return_value=mock_result)
        
        # Test data
        entity_relationships = [
            {"a": "Bitcoin", "b": "Ethereum", "weight": 5},
            {"a": "Bitcoin", "b": "Coinbase", "weight": 3},
        ]
        
        # Call upsert_narrative
        narrative_id = await upsert_narrative(
            theme="test_theme",
            title="Test Narrative",
            summary="Test summary",
            entities=["Bitcoin", "Ethereum", "Coinbase"],
            article_ids=["article1", "article2"],
            article_count=2,
            mention_velocity=1.5,
            lifecycle="emerging",
            momentum="growing",
            recency_score=0.9,
            entity_relationships=entity_relationships
        )
        
        # Verify insert was called
        assert mock_collection.insert_one.called
        
        # Verify entity_relationships was included in the document
        call_args = mock_collection.insert_one.call_args[0][0]
        assert "entity_relationships" in call_args
        assert call_args["entity_relationships"] == entity_relationships


@pytest.mark.asyncio
async def test_upsert_narrative_updates_entity_relationships():
    """Test that upsert_narrative updates entity relationships for existing narratives."""
    with patch("crypto_news_aggregator.db.operations.narratives.mongo_manager") as mock_mongo:
        # Mock database
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.narratives = mock_collection
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Mock find_one to return existing narrative
        existing_narrative = {
            "_id": "narrative123",
            "theme": "test_theme",
            "first_seen": datetime.now(timezone.utc),
            "timeline_data": [],
            "peak_activity": {}
        }
        mock_collection.find_one = AsyncMock(return_value=existing_narrative)
        mock_collection.update_one = AsyncMock()
        
        # New relationships
        new_relationships = [
            {"a": "Bitcoin", "b": "Ethereum", "weight": 7},
            {"a": "Bitcoin", "b": "MicroStrategy", "weight": 4},
        ]
        
        # Call upsert_narrative
        await upsert_narrative(
            theme="test_theme",
            title="Updated Narrative",
            summary="Updated summary",
            entities=["Bitcoin", "Ethereum", "MicroStrategy"],
            article_ids=["article1", "article2", "article3"],
            article_count=3,
            mention_velocity=2.0,
            lifecycle="hot",
            momentum="growing",
            recency_score=0.95,
            entity_relationships=new_relationships
        )
        
        # Verify update was called
        assert mock_collection.update_one.called
        
        # Verify entity_relationships was updated
        call_args = mock_collection.update_one.call_args[0]
        update_data = call_args[1]["$set"]
        assert "entity_relationships" in update_data
        assert update_data["entity_relationships"] == new_relationships


@pytest.mark.asyncio
async def test_upsert_narrative_defaults_empty_relationships():
    """Test that upsert_narrative defaults to empty list if no relationships provided."""
    with patch("crypto_news_aggregator.db.operations.narratives.mongo_manager") as mock_mongo:
        # Mock database
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.narratives = mock_collection
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Mock find_one to return None (new narrative)
        mock_collection.find_one = AsyncMock(return_value=None)
        
        # Mock insert_one
        mock_result = MagicMock()
        mock_result.inserted_id = "narrative123"
        mock_collection.insert_one = AsyncMock(return_value=mock_result)
        
        # Call upsert_narrative WITHOUT entity_relationships
        await upsert_narrative(
            theme="test_theme",
            title="Test Narrative",
            summary="Test summary",
            entities=["Bitcoin"],
            article_ids=["article1"],
            article_count=1,
            mention_velocity=1.0,
            lifecycle="emerging",
            momentum="stable",
            recency_score=0.8
            # entity_relationships NOT provided
        )
        
        # Verify insert was called
        assert mock_collection.insert_one.called
        
        # Verify entity_relationships defaults to empty list
        call_args = mock_collection.insert_one.call_args[0][0]
        assert "entity_relationships" in call_args
        assert call_args["entity_relationships"] == []
