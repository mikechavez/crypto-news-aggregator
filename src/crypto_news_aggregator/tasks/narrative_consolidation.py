"""
Narrative consolidation task - merges duplicate narratives.

Runs every 1 hour to catch edge cases where similar narratives
slipped through initial detection.
"""

import asyncio

from celery.utils.log import get_task_logger
from celery import shared_task

from crypto_news_aggregator.services.narrative_service import consolidate_duplicate_narratives

logger = get_task_logger(__name__)


@shared_task(name="consolidate_narratives")
def consolidate_narratives_task():
    """
    Find and merge duplicate narratives with similarity ≥0.9.

    Runs every 1 hour as a safety net for edge cases.
    """
    logger.info("Starting narrative consolidation task")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_run_consolidation())

        logger.info(
            f"Consolidation complete: {result['merge_count']} merges, "
            f"{len(result['errors'])} errors"
        )

        # Log merged pairs for monitoring
        for pair in result["merged_pairs"]:
            logger.info(
                f"Merged: {pair['merged']} → {pair['survivor']} "
                f"(similarity={pair['similarity']:.3f})"
            )

        return result

    except Exception as e:
        logger.error(f"Consolidation task failed: {e}", exc_info=True)
        raise
    finally:
        loop.close()


async def _run_consolidation():
    """Async wrapper for consolidation logic."""
    # Run the consolidation function from narrative_service
    result = await consolidate_duplicate_narratives()
    return result
