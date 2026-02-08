"""
Celery tasks for generating daily crypto briefings.

Schedule:
- Morning briefing: 8:00 AM EST (13:00 UTC)
- Evening briefing: 8:00 PM EST (01:00 UTC next day)

Note: EST is UTC-5, but we use America/New_York timezone to handle DST automatically.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from celery import shared_task

from crypto_news_aggregator.db.mongodb import initialize_mongodb, mongo_manager
from crypto_news_aggregator.services.briefing_agent import (
    get_briefing_agent,
    generate_morning_briefing,
    generate_evening_briefing,
)

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async code with proper event loop handling for Celery workers."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)  # Set as current so Motor can find it
    try:
        return loop.run_until_complete(coro)
    finally:
        asyncio.set_event_loop(None)  # Clear before closing
        loop.close()


async def _ensure_mongodb():
    """Ensure MongoDB is initialized."""
    try:
        db = await mongo_manager.get_async_database()
        return True
    except Exception:
        await initialize_mongodb()
        return True


async def _generate_morning_briefing_async() -> Optional[Dict[str, Any]]:
    """Async implementation of morning briefing generation."""
    await _ensure_mongodb()
    return await generate_morning_briefing(force=False)


async def _generate_evening_briefing_async() -> Optional[Dict[str, Any]]:
    """Async implementation of evening briefing generation."""
    await _ensure_mongodb()
    return await generate_evening_briefing(force=False)


@shared_task(
    name="generate_morning_briefing",
    bind=True,
    max_retries=2,
    default_retry_delay=300,  # 5 minutes
)
def generate_morning_briefing_task(self) -> Dict[str, Any]:
    """
    Generate the morning crypto briefing.

    Scheduled to run at 8:00 AM EST (13:00 UTC) every day.
    If generation fails, retries up to 2 times with 5-minute delay.

    Returns:
        Dict with generation result or error info
    """
    logger.info("Starting morning briefing generation task")
    start_time = datetime.now(timezone.utc)

    try:
        briefing = _run_async(_generate_morning_briefing_async())

        if briefing:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Morning briefing generated successfully in {duration:.1f}s, "
                f"ID: {briefing.get('_id')}"
            )
            return {
                "status": "success",
                "briefing_id": str(briefing.get("_id")),
                "generated_at": briefing.get("generated_at").isoformat(),
                "duration_seconds": duration,
            }
        else:
            logger.info("Morning briefing skipped (already exists for today)")
            return {
                "status": "skipped",
                "reason": "briefing_already_exists",
            }

    except Exception as exc:
        logger.exception(f"Morning briefing generation failed: {exc}")
        # Retry on failure
        raise self.retry(exc=exc)


@shared_task(
    name="generate_evening_briefing",
    bind=True,
    max_retries=2,
    default_retry_delay=300,  # 5 minutes
)
def generate_evening_briefing_task(self) -> Dict[str, Any]:
    """
    Generate the evening crypto briefing.

    Scheduled to run at 8:00 PM EST (01:00 UTC next day) every day.
    If generation fails, retries up to 2 times with 5-minute delay.

    Returns:
        Dict with generation result or error info
    """
    logger.info("Starting evening briefing generation task")
    start_time = datetime.now(timezone.utc)

    try:
        briefing = _run_async(_generate_evening_briefing_async())

        if briefing:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Evening briefing generated successfully in {duration:.1f}s, "
                f"ID: {briefing.get('_id')}"
            )
            return {
                "status": "success",
                "briefing_id": str(briefing.get("_id")),
                "generated_at": briefing.get("generated_at").isoformat(),
                "duration_seconds": duration,
            }
        else:
            logger.info("Evening briefing skipped (already exists for today)")
            return {
                "status": "skipped",
                "reason": "briefing_already_exists",
            }

    except Exception as exc:
        logger.exception(f"Evening briefing generation failed: {exc}")
        # Retry on failure
        raise self.retry(exc=exc)


@shared_task(
    name="force_generate_briefing",
)
def force_generate_briefing_task(briefing_type: str = "morning") -> Dict[str, Any]:
    """
    Force generate a briefing (for manual/admin use).

    Args:
        briefing_type: "morning" or "evening"

    Returns:
        Dict with generation result
    """
    logger.info(f"Force generating {briefing_type} briefing")
    start_time = datetime.now(timezone.utc)

    async def _force_generate():
        await _ensure_mongodb()
        agent = get_briefing_agent()
        return await agent.generate_briefing(briefing_type, force=True)

    try:
        briefing = _run_async(_force_generate())

        if briefing:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Force {briefing_type} briefing generated in {duration:.1f}s"
            )
            return {
                "status": "success",
                "briefing_id": str(briefing.get("_id")),
                "briefing_type": briefing_type,
                "generated_at": briefing.get("generated_at").isoformat(),
                "duration_seconds": duration,
            }
        else:
            return {
                "status": "failed",
                "reason": "generation_returned_none",
            }

    except Exception as exc:
        logger.exception(f"Force briefing generation failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
        }


@shared_task(
    name="cleanup_old_briefings",
)
def cleanup_old_briefings_task(retention_days: int = 30) -> Dict[str, Any]:
    """
    Clean up old briefings beyond retention period.

    Args:
        retention_days: Number of days to keep briefings

    Returns:
        Dict with cleanup result
    """
    from crypto_news_aggregator.db.operations.briefing import cleanup_old_briefings

    logger.info(f"Cleaning up briefings older than {retention_days} days")

    async def _cleanup():
        await _ensure_mongodb()
        return await cleanup_old_briefings(retention_days=retention_days)

    try:
        deleted_count = _run_async(_cleanup())
        logger.info(f"Cleaned up {deleted_count} old briefings")
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "retention_days": retention_days,
        }
    except Exception as exc:
        logger.exception(f"Briefing cleanup failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
        }
