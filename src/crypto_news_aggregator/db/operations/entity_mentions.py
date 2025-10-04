from typing import List, Dict, Any
from datetime import datetime, timezone
from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.db.models import EntityType


async def create_entity_mention(
    entity: str,
    entity_type: str,
    article_id: str,
    sentiment: str,
    confidence: float = 1.0,
    is_primary: bool = None,
    metadata: Dict[str, Any] = None,
) -> str:
    """
    Creates a new entity mention record in the database.

    Args:
        entity: The entity name/value (e.g., "$BTC", "Bitcoin", "regulation")
        entity_type: Type of entity (one of EntityType values)
        article_id: ID of the article where entity was mentioned
        sentiment: Sentiment of the mention (positive, negative, neutral)
        confidence: Confidence score of the extraction (0.0-1.0)
        is_primary: Whether this is a primary entity (auto-determined if None)
        metadata: Additional metadata about the mention

    Returns:
        The ID of the created entity mention
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_mentions

    # Auto-determine is_primary if not provided
    if is_primary is None:
        is_primary = EntityType.is_primary(entity_type)

    mention_data = {
        "entity": entity,
        "entity_type": entity_type,
        "article_id": article_id,
        "sentiment": sentiment,
        "confidence": confidence,
        "is_primary": is_primary,
        "timestamp": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "metadata": metadata or {},
    }

    result = await collection.insert_one(mention_data)
    return str(result.inserted_id)


async def create_entity_mentions_batch(mentions: List[Dict[str, Any]]) -> List[str]:
    """
    Creates multiple entity mention records in a single batch operation.

    Args:
        mentions: List of mention dicts with keys: entity, entity_type, article_id, sentiment, confidence, is_primary (optional)

    Returns:
        List of created mention IDs
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_mentions

    now = datetime.now(timezone.utc)
    mention_docs = []

    for mention in mentions:
        entity_type = mention["entity_type"]
        # Auto-determine is_primary if not provided
        is_primary = mention.get("is_primary")
        if is_primary is None:
            is_primary = EntityType.is_primary(entity_type)

        mention_doc = {
            "entity": mention["entity"],
            "entity_type": entity_type,
            "article_id": mention["article_id"],
            "sentiment": mention.get("sentiment", "neutral"),
            "confidence": mention.get("confidence", 1.0),
            "is_primary": is_primary,
            "timestamp": now,
            "created_at": now,
            "metadata": mention.get("metadata", {}),
        }
        mention_docs.append(mention_doc)

    if mention_docs:
        result = await collection.insert_many(mention_docs)
        return [str(id) for id in result.inserted_ids]
    return []


async def get_entity_mentions(
    entity: str = None,
    entity_type: str = None,
    article_id: str = None,
    sentiment: str = None,
    is_primary: bool = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Retrieves entity mentions based on filters.

    Args:
        entity: Filter by specific entity
        entity_type: Filter by entity type
        article_id: Filter by article ID
        sentiment: Filter by sentiment
        is_primary: Filter by primary entity flag
        limit: Maximum number of results

    Returns:
        List of entity mention documents
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_mentions

    query = {}
    if entity:
        query["entity"] = entity
    if entity_type:
        query["entity_type"] = entity_type
    if article_id:
        query["article_id"] = article_id
    if sentiment:
        query["sentiment"] = sentiment
    if is_primary is not None:
        query["is_primary"] = is_primary

    cursor = collection.find(query).sort("timestamp", -1).limit(limit)
    mentions = []
    async for mention in cursor:
        mention["_id"] = str(mention["_id"])
        mentions.append(mention)

    return mentions


async def get_entity_stats(entity: str) -> Dict[str, Any]:
    """
    Gets aggregated statistics for a specific entity.

    Args:
        entity: The entity to get stats for

    Returns:
        Dict with mention count, sentiment distribution, and recent mentions
    """
    db = await mongo_manager.get_async_database()
    collection = db.entity_mentions

    # Count total mentions
    total_count = await collection.count_documents({"entity": entity})

    # Get sentiment distribution
    pipeline = [
        {"$match": {"entity": entity}},
        {"$group": {"_id": "$sentiment", "count": {"$sum": 1}}},
    ]
    sentiment_dist = {}
    async for result in collection.aggregate(pipeline):
        sentiment_dist[result["_id"]] = result["count"]

    # Get recent mentions
    recent_cursor = collection.find({"entity": entity}).sort("timestamp", -1).limit(10)
    recent_mentions = []
    async for mention in recent_cursor:
        mention["_id"] = str(mention["_id"])
        recent_mentions.append(mention)

    return {
        "entity": entity,
        "total_mentions": total_count,
        "sentiment_distribution": sentiment_dist,
        "recent_mentions": recent_mentions,
    }
