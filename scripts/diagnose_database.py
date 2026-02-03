#!/usr/bin/env python3
"""
Diagnostic script to verify MongoDB connection and check collection status.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


async def diagnose_database():
    """Check MongoDB connection and collection status."""

    # Get connection URI
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        logger.error("MONGODB_URI not set in environment")
        return False

    logger.info("Attempting to connect to MongoDB...")
    logger.info(f"URI: {mongo_uri[:50]}...")

    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)

        # Test connection by getting server info
        admin_db = client["admin"]
        await admin_db.command("ping")
        logger.info("✓ Successfully connected to MongoDB")

        # Get database
        db = client["backdrop"]

        # Check collections
        logger.info("\n" + "="*60)
        logger.info("Collection Status")
        logger.info("="*60)

        collections = await db.list_collection_names()
        logger.info(f"Available collections: {len(collections)}")
        for coll in sorted(collections):
            logger.info(f"  - {coll}")

        # Check key collections
        logger.info("\n" + "="*60)
        logger.info("Key Collections Analysis")
        logger.info("="*60)

        # Articles
        article_count = await db.articles.count_documents({})
        logger.info(f"\narticles: {article_count} documents")
        if article_count > 0:
            recent_articles = await db.articles.count_documents({
                "published_at": {"$gte": datetime.now(timezone.utc) - timedelta(days=7)}
            })
            logger.info(f"  - Last 7 days: {recent_articles}")

        # Narratives
        narrative_count = await db.narratives.count_documents({})
        logger.info(f"\nnarratives: {narrative_count} documents")

        without_focus = 0
        if narrative_count > 0:
            without_focus = await db.narratives.count_documents({
                "narrative_focus": {"$exists": False}
            })
            with_focus = narrative_count - without_focus
            logger.info(f"  - With narrative_focus: {with_focus}")
            logger.info(f"  - Missing narrative_focus: {without_focus}")

            recent_narratives = await db.narratives.count_documents({
                "first_detected_at": {"$gte": datetime(2025, 12, 1, tzinfo=timezone.utc)}
            })
            logger.info(f"  - Created since Dec 1, 2025: {recent_narratives}")

        # Entity mentions
        entity_mention_count = await db.entity_mentions.count_documents({})
        logger.info(f"\nentity_mentions: {entity_mention_count} documents")

        # Analyst notes
        notes_count = await db.analyst_notes.count_documents({})
        logger.info(f"\nanalyst_notes: {notes_count} documents")

        # Signals
        signal_count = await db.signals.count_documents({})
        logger.info(f"\nsignals: {signal_count} documents")

        # Summary
        logger.info("\n" + "="*60)
        logger.info("Database Status Summary")
        logger.info("="*60)

        if article_count < 1000:
            logger.warning("⚠️  Articles count is LOW (< 1000)")
        else:
            logger.info(f"✓ Articles count is healthy: {article_count:,}")

        if narrative_count < 50:
            logger.warning("⚠️  Narratives count is LOW (< 50)")
        else:
            logger.info(f"✓ Narratives count is healthy: {narrative_count:,}")

        if without_focus > 0:
            logger.info(f"\n→ Ready to backfill {without_focus} narratives missing narrative_focus")
        else:
            logger.warning("⚠️  No narratives found without narrative_focus field")

        logger.info("\n✓ Database diagnostic complete")
        return True

    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        logger.error("This may indicate:")
        logger.error("  - Wrong MONGODB_URI")
        logger.error("  - Network connectivity issue")
        logger.error("  - MongoDB Atlas cluster not accessible")
        return False
    finally:
        client.close()


async def main():
    """Run diagnostic."""
    success = await diagnose_database()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
