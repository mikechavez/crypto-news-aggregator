"""
Tests for entity_mentions database operations.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from crypto_news_aggregator.db.operations.entity_mentions import (
    create_entity_mention,
    create_entity_mentions_batch,
    get_entity_mentions,
    get_entity_stats,
)


@pytest.mark.asyncio
async def test_create_entity_mention(mongo_db):
    """Test creating a single entity mention."""
    mention_id = await create_entity_mention(
        entity="$BTC",
        entity_type="ticker",
        article_id="article_123",
        sentiment="positive",
        confidence=0.95,
        metadata={"source": "test"}
    )
    
    assert mention_id is not None
    
    # Verify the mention was created
    collection = mongo_db.entity_mentions
    mention = await collection.find_one({"entity": "$BTC"})
    assert mention is not None
    assert mention["entity_type"] == "ticker"
    assert mention["article_id"] == "article_123"
    assert mention["sentiment"] == "positive"
    assert mention["confidence"] == 0.95


@pytest.mark.asyncio
async def test_create_entity_mentions_batch(mongo_db):
    """Test creating multiple entity mentions in a batch."""
    mentions = [
        {
            "entity": "$BTC",
            "entity_type": "ticker",
            "article_id": "article_1",
            "sentiment": "positive",
            "confidence": 0.95,
        },
        {
            "entity": "$ETH",
            "entity_type": "ticker",
            "article_id": "article_2",
            "sentiment": "neutral",
            "confidence": 0.90,
        },
        {
            "entity": "Bitcoin",
            "entity_type": "project",
            "article_id": "article_1",
            "sentiment": "positive",
            "confidence": 0.95,
        }
    ]
    
    mention_ids = await create_entity_mentions_batch(mentions)
    
    assert len(mention_ids) == 3
    
    # Verify all mentions were created
    collection = mongo_db.entity_mentions
    count = await collection.count_documents({})
    assert count == 3


@pytest.mark.asyncio
async def test_create_entity_mentions_batch_empty():
    """Test creating entity mentions with empty list."""
    mention_ids = await create_entity_mentions_batch([])
    assert mention_ids == []


@pytest.mark.asyncio
async def test_get_entity_mentions_by_entity(mongo_db):
    """Test retrieving entity mentions filtered by entity."""
    # Create test mentions
    await create_entity_mentions_batch([
        {"entity": "$BTC", "entity_type": "ticker", "article_id": "article_1", "sentiment": "positive"},
        {"entity": "$BTC", "entity_type": "ticker", "article_id": "article_2", "sentiment": "negative"},
        {"entity": "$ETH", "entity_type": "ticker", "article_id": "article_3", "sentiment": "neutral"},
    ])
    
    # Get mentions for $BTC
    btc_mentions = await get_entity_mentions(entity="$BTC")
    
    assert len(btc_mentions) == 2
    assert all(m["entity"] == "$BTC" for m in btc_mentions)


@pytest.mark.asyncio
async def test_get_entity_mentions_by_type(mongo_db):
    """Test retrieving entity mentions filtered by type."""
    # Create test mentions
    await create_entity_mentions_batch([
        {"entity": "$BTC", "entity_type": "ticker", "article_id": "article_1", "sentiment": "positive"},
        {"entity": "Bitcoin", "entity_type": "project", "article_id": "article_1", "sentiment": "positive"},
        {"entity": "regulation", "entity_type": "event", "article_id": "article_1", "sentiment": "negative"},
    ])
    
    # Get ticker mentions
    ticker_mentions = await get_entity_mentions(entity_type="ticker")
    
    assert len(ticker_mentions) == 1
    assert ticker_mentions[0]["entity_type"] == "ticker"


@pytest.mark.asyncio
async def test_get_entity_mentions_by_article(mongo_db):
    """Test retrieving entity mentions filtered by article ID."""
    # Create test mentions
    await create_entity_mentions_batch([
        {"entity": "$BTC", "entity_type": "ticker", "article_id": "article_1", "sentiment": "positive"},
        {"entity": "$ETH", "entity_type": "ticker", "article_id": "article_1", "sentiment": "positive"},
        {"entity": "$SOL", "entity_type": "ticker", "article_id": "article_2", "sentiment": "neutral"},
    ])
    
    # Get mentions for article_1
    article_mentions = await get_entity_mentions(article_id="article_1")
    
    assert len(article_mentions) == 2
    assert all(m["article_id"] == "article_1" for m in article_mentions)


@pytest.mark.asyncio
async def test_get_entity_mentions_by_sentiment(mongo_db):
    """Test retrieving entity mentions filtered by sentiment."""
    # Create test mentions
    await create_entity_mentions_batch([
        {"entity": "$BTC", "entity_type": "ticker", "article_id": "article_1", "sentiment": "positive"},
        {"entity": "$ETH", "entity_type": "ticker", "article_id": "article_2", "sentiment": "positive"},
        {"entity": "$SOL", "entity_type": "ticker", "article_id": "article_3", "sentiment": "negative"},
    ])
    
    # Get positive mentions
    positive_mentions = await get_entity_mentions(sentiment="positive")
    
    assert len(positive_mentions) == 2
    assert all(m["sentiment"] == "positive" for m in positive_mentions)


@pytest.mark.asyncio
async def test_get_entity_mentions_limit(mongo_db):
    """Test that limit parameter works correctly."""
    # Create many mentions
    mentions = [
        {"entity": "$BTC", "entity_type": "ticker", "article_id": f"article_{i}", "sentiment": "positive"}
        for i in range(20)
    ]
    await create_entity_mentions_batch(mentions)
    
    # Get with limit
    limited_mentions = await get_entity_mentions(entity="$BTC", limit=5)
    
    assert len(limited_mentions) == 5


@pytest.mark.asyncio
async def test_get_entity_stats(mongo_db):
    """Test getting aggregated statistics for an entity."""
    # Create test mentions with different sentiments
    await create_entity_mentions_batch([
        {"entity": "$BTC", "entity_type": "ticker", "article_id": "article_1", "sentiment": "positive"},
        {"entity": "$BTC", "entity_type": "ticker", "article_id": "article_2", "sentiment": "positive"},
        {"entity": "$BTC", "entity_type": "ticker", "article_id": "article_3", "sentiment": "negative"},
        {"entity": "$BTC", "entity_type": "ticker", "article_id": "article_4", "sentiment": "neutral"},
    ])
    
    stats = await get_entity_stats("$BTC")
    
    assert stats["entity"] == "$BTC"
    assert stats["total_mentions"] == 4
    assert stats["sentiment_distribution"]["positive"] == 2
    assert stats["sentiment_distribution"]["negative"] == 1
    assert stats["sentiment_distribution"]["neutral"] == 1
    assert len(stats["recent_mentions"]) == 4


@pytest.mark.asyncio
async def test_get_entity_stats_no_mentions(mongo_db):
    """Test getting stats for an entity with no mentions."""
    stats = await get_entity_stats("$NONEXISTENT")
    
    assert stats["entity"] == "$NONEXISTENT"
    assert stats["total_mentions"] == 0
    assert stats["sentiment_distribution"] == {}
    assert stats["recent_mentions"] == []


@pytest.mark.asyncio
async def test_entity_mention_timestamps(mongo_db):
    """Test that timestamps are properly set on entity mentions."""
    mention_id = await create_entity_mention(
        entity="$BTC",
        entity_type="ticker",
        article_id="article_1",
        sentiment="positive"
    )
    
    collection = mongo_db.entity_mentions
    mention = await collection.find_one({"entity": "$BTC"})
    
    assert "timestamp" in mention
    assert "created_at" in mention
    assert isinstance(mention["timestamp"], datetime)
    assert isinstance(mention["created_at"], datetime)


@pytest.mark.asyncio
async def test_entity_mention_metadata(mongo_db):
    """Test that metadata is properly stored."""
    metadata = {
        "article_title": "Bitcoin Soars",
        "extraction_batch": True,
        "custom_field": "test_value"
    }
    
    mention_id = await create_entity_mention(
        entity="$BTC",
        entity_type="ticker",
        article_id="article_1",
        sentiment="positive",
        metadata=metadata
    )
    
    collection = mongo_db.entity_mentions
    mention = await collection.find_one({"entity": "$BTC"})
    
    assert mention["metadata"] == metadata
