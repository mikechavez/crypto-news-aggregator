"""
Process articles without narrative_summary through narrative detection.

This script:
1. Queries articles where narrative_summary is null/empty
2. Extracts narrative elements (actors, nucleus_entity, tensions, etc.)
3. Matches to existing narratives using fingerprint similarity (0.6 threshold)
4. Creates new narratives if similarity is below threshold
"""
import asyncio
import sys
from pathlib import Path
import logging
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_news_aggregator.services.narrative_themes import (
    discover_narrative_from_article,
    calculate_fingerprint_similarity,
    compute_narrative_fingerprint
)
from crypto_news_aggregator.db.mongodb import mongo_manager


async def find_matching_narrative(article_fingerprint: dict, db) -> tuple[str, float]:
    """
    Find best matching narrative for an article based on fingerprint similarity.
    
    Args:
        article_fingerprint: Fingerprint dict with nucleus_entity, top_actors, key_actions
        db: MongoDB database instance
    
    Returns:
        Tuple of (narrative_id, similarity_score) or (None, 0.0) if no match
    """
    narratives_collection = db.narratives
    
    # Get all active narratives with fingerprints
    cursor = narratives_collection.find({
        "fingerprint": {"$exists": True},
        "lifecycle_state": {"$in": ["emerging", "hot", "mature", "declining"]}
    })
    
    narratives = await cursor.to_list(length=None)
    
    best_match_id = None
    best_similarity = 0.0
    
    for narrative in narratives:
        narrative_fingerprint = narrative.get("fingerprint", {})
        if not narrative_fingerprint:
            continue
        
        similarity = calculate_fingerprint_similarity(
            article_fingerprint,
            narrative_fingerprint
        )
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match_id = str(narrative["_id"])
    
    return best_match_id, best_similarity


async def process_missing_narratives():
    """Process articles without narrative_summary."""
    
    logger.info("🔌 Connecting to MongoDB...")
    await mongo_manager.initialize()
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    narratives_collection = db.narratives
    
    # Find articles without narrative_summary
    cursor = articles_collection.find({
        "$or": [
            {"narrative_summary": {"$exists": False}},
            {"narrative_summary": None},
            {"narrative_summary": ""}
        ]
    }).sort("published_at", -1)
    
    articles = await cursor.to_list(length=None)
    total_articles = len(articles)
    
    logger.info(f"📊 Found {total_articles} articles without narrative_summary")
    
    if total_articles == 0:
        logger.info("✅ No articles to process")
        await mongo_manager.close()
        return
    
    # Statistics
    stats = {
        "processed": 0,
        "matched_to_existing": 0,
        "created_new": 0,
        "failed": 0,
        "matches": []  # Track matches for reporting
    }
    
    logger.info(f"\n🔄 Processing {total_articles} articles...\n")
    
    for idx, article in enumerate(articles, 1):
        article_id = str(article.get("_id"))
        title = article.get("title", "Unknown")[:60]
        
        logger.info(f"[{idx}/{total_articles}] Processing: {title}...")
        
        try:
            # Step 1: Extract narrative elements
            narrative_data = await discover_narrative_from_article(article)
            
            if not narrative_data:
                logger.warning(f"  ❌ Failed to extract narrative data")
                stats["failed"] += 1
                continue
            
            # Update article with narrative data
            await articles_collection.update_one(
                {"_id": article["_id"]},
                {"$set": {
                    "actors": narrative_data.get("actors", []),
                    "actor_salience": narrative_data.get("actor_salience", {}),
                    "nucleus_entity": narrative_data.get("nucleus_entity", ""),
                    "narrative_focus": narrative_data.get("narrative_focus", ""),
                    "actions": narrative_data.get("actions", []),
                    "tensions": narrative_data.get("tensions", []),
                    "implications": narrative_data.get("implications", ""),
                    "narrative_summary": narrative_data.get("narrative_summary", ""),
                    "narrative_hash": narrative_data.get("narrative_hash", ""),
                    "narrative_extracted_at": datetime.now(timezone.utc)
                }}
            )
            
            logger.info(f"  ✓ Extracted narrative: {narrative_data.get('nucleus_entity', 'Unknown')}")
            
            # Step 2: Compute fingerprint for matching
            cluster_data = {
                "nucleus_entity": narrative_data.get("nucleus_entity", ""),
                "narrative_focus": narrative_data.get("narrative_focus", ""),
                "actors": narrative_data.get("actor_salience", {}),
                "actions": narrative_data.get("actions", [])
            }
            article_fingerprint = compute_narrative_fingerprint(cluster_data)
            
            # Step 3: Find matching narrative
            narrative_id, similarity = await find_matching_narrative(article_fingerprint, db)
            
            # Step 4: Match or create based on 0.6 threshold
            if narrative_id and similarity >= 0.6:
                # Match to existing narrative
                logger.info(f"  ✓ Matched to existing narrative (similarity: {similarity:.2f})")
                
                # Add article to narrative's article list
                await narratives_collection.update_one(
                    {"_id": narrative_id},
                    {
                        "$addToSet": {"article_ids": article_id},
                        "$set": {"last_updated": datetime.now(timezone.utc)}
                    }
                )
                
                # Update article with narrative_id
                await articles_collection.update_one(
                    {"_id": article["_id"]},
                    {"$set": {"narrative_id": narrative_id}}
                )
                
                stats["matched_to_existing"] += 1
                stats["matches"].append({
                    "article_id": article_id,
                    "title": title,
                    "narrative_id": narrative_id,
                    "similarity": similarity,
                    "action": "matched"
                })
            else:
                # Create new narrative (similarity < 0.6 or no match found)
                logger.info(f"  ✓ Creating new narrative (similarity: {similarity:.2f})")
                
                new_narrative = {
                    "nucleus_entity": narrative_data.get("nucleus_entity", ""),
                    "actors": narrative_data.get("actor_salience", {}),
                    "actions": narrative_data.get("actions", []),
                    "tensions": narrative_data.get("tensions", []),
                    "narrative_summary": narrative_data.get("narrative_summary", ""),
                    "fingerprint": article_fingerprint,
                    "article_ids": [article_id],
                    "article_count": 1,
                    "lifecycle_state": "emerging",
                    "first_seen": article.get("published_at"),
                    "last_updated": datetime.now(timezone.utc),
                    "created_at": datetime.now(timezone.utc)
                }
                
                result = await narratives_collection.insert_one(new_narrative)
                new_narrative_id = str(result.inserted_id)
                
                # Update article with narrative_id
                await articles_collection.update_one(
                    {"_id": article["_id"]},
                    {"$set": {"narrative_id": new_narrative_id}}
                )
                
                stats["created_new"] += 1
                stats["matches"].append({
                    "article_id": article_id,
                    "title": title,
                    "narrative_id": new_narrative_id,
                    "similarity": similarity,
                    "action": "created_new"
                })
            
            stats["processed"] += 1
            
            # Rate limiting: 1 second between articles
            if idx < total_articles:
                await asyncio.sleep(1.0)
        
        except Exception as e:
            logger.error(f"  ❌ Error processing article: {str(e)}", exc_info=True)
            stats["failed"] += 1
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 PROCESSING SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total articles processed: {stats['processed']}")
    logger.info(f"Matched to existing narratives: {stats['matched_to_existing']}")
    logger.info(f"Created new narratives: {stats['created_new']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"{'='*60}\n")
    
    # Print detailed matches
    if stats["matches"]:
        logger.info(f"📋 DETAILED MATCHES:")
        for match in stats["matches"]:
            action_emoji = "🔗" if match["action"] == "matched" else "✨"
            logger.info(
                f"{action_emoji} {match['title'][:50]:<50} | "
                f"Similarity: {match['similarity']:.2f} | "
                f"Action: {match['action']}"
            )
    
    await mongo_manager.close()
    logger.info("\n✅ Processing complete!")


if __name__ == "__main__":
    asyncio.run(process_missing_narratives())
