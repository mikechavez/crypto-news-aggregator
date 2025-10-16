#!/usr/bin/env python3
"""
Backfill key_actions for existing narratives.

This script extracts key actions from narrative summaries for narratives
that have empty key_actions arrays in their fingerprints. This is necessary
because empty key_actions prevent narratives from reaching the 0.6 similarity
threshold needed for matching.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.core.config import settings
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_actions_from_summary(summary: str, api_key: str) -> List[str]:
    """
    Extract 2-3 key actions from a narrative summary using Claude Haiku.
    
    Args:
        summary: The narrative summary text
        api_key: Anthropic API key
    
    Returns:
        List of 2-3 action strings (e.g., ["filed lawsuit", "announced partnership"])
    """
    prompt = f"""Extract 2-3 key actions or events from this crypto narrative summary.
Return ONLY a JSON array of short action phrases (2-4 words each).

Examples of good actions:
- "filed lawsuit"
- "announced partnership"
- "launched mainnet"
- "regulatory enforcement"
- "price rally"
- "network upgrade"

Summary:
{summary}

Return ONLY the JSON array, no other text. Example format:
["action one", "action two", "action three"]"""

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    
    payload = {
        "model": settings.ANTHROPIC_DEFAULT_MODEL,  # Use Haiku
        "max_tokens": 256,
        "messages": [{"role": "user", "content": prompt}],
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            response_text = data.get("content", [{}])[0].get("text", "")
            
            # Parse JSON response
            import re
            # Try to extract JSON array from response
            json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if json_match:
                actions = json.loads(json_match.group(0))
            else:
                actions = json.loads(response_text)
            
            # Validate and clean actions
            if isinstance(actions, list):
                # Filter to 2-3 actions, ensure they're strings
                actions = [str(a).strip() for a in actions if a][:3]
                return actions
            else:
                logger.warning(f"Invalid response format: {response_text}")
                return []
                
    except httpx.HTTPStatusError as e:
        logger.error(f"Anthropic API request failed: {e.response.status_code} - {e.response.text}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error extracting actions: {e}")
        return []


async def backfill_narrative_actions():
    """
    Backfill key_actions for all narratives with empty key_actions arrays.
    """
    logger.info("Starting narrative actions backfill...")
    
    # Check for API key
    if not settings.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not configured in environment")
        return
    
    # Get database connection
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives
    
    # Find narratives with empty or missing key_actions
    query = {
        "$or": [
            {"fingerprint.key_actions": {"$exists": False}},
            {"fingerprint.key_actions": []},
            {"fingerprint.key_actions": None}
        ]
    }
    
    cursor = narratives_collection.find(query)
    narratives = await cursor.to_list(length=None)
    
    total_count = len(narratives)
    logger.info(f"Found {total_count} narratives with empty key_actions")
    
    if total_count == 0:
        logger.info("No narratives need backfilling. Exiting.")
        return
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for idx, narrative in enumerate(narratives, 1):
        narrative_id = narrative.get("_id")
        theme = narrative.get("theme", "unknown")
        summary = narrative.get("summary", "")
        
        # Skip if no summary
        if not summary:
            logger.warning(f"[{idx}/{total_count}] Skipping narrative {narrative_id} (theme: {theme}) - no summary")
            skipped_count += 1
            continue
        
        try:
            # Extract actions from summary
            logger.info(f"[{idx}/{total_count}] Processing narrative {narrative_id} (theme: {theme})")
            actions = extract_actions_from_summary(summary, settings.ANTHROPIC_API_KEY)
            
            if not actions:
                logger.warning(f"[{idx}/{total_count}] No actions extracted for narrative {narrative_id}")
                error_count += 1
                # Rate limit even on errors
                time.sleep(1)
                continue
            
            # Update the narrative's fingerprint
            fingerprint = narrative.get("fingerprint", {})
            if not fingerprint:
                # Create a basic fingerprint if it doesn't exist
                fingerprint = {
                    "nucleus_entity": narrative.get("theme", ""),
                    "top_actors": narrative.get("entities", [])[:5],
                    "key_actions": actions,
                    "timestamp": datetime.now(timezone.utc)
                }
            else:
                # Update existing fingerprint
                fingerprint["key_actions"] = actions
                fingerprint["timestamp"] = datetime.now(timezone.utc)
            
            # Update in database
            result = await narratives_collection.update_one(
                {"_id": narrative_id},
                {"$set": {"fingerprint": fingerprint}}
            )
            
            if result.modified_count > 0:
                logger.info(f"[{idx}/{total_count}] ✓ Updated narrative {narrative_id} with actions: {actions}")
                updated_count += 1
            else:
                logger.warning(f"[{idx}/{total_count}] No update performed for narrative {narrative_id}")
                error_count += 1
            
        except Exception as e:
            logger.error(f"[{idx}/{total_count}] Error processing narrative {narrative_id}: {e}")
            error_count += 1
        
        # Rate limiting: 1 second between API calls
        time.sleep(1)
        
        # Log progress every 10 narratives
        if idx % 10 == 0:
            logger.info(f"Progress: {idx}/{total_count} processed, {updated_count} updated, {skipped_count} skipped, {error_count} errors")
    
    # Final summary
    logger.info("=" * 80)
    logger.info("Backfill complete!")
    logger.info(f"Total narratives: {total_count}")
    logger.info(f"Successfully updated: {updated_count}")
    logger.info(f"Skipped (no summary): {skipped_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("=" * 80)


async def main():
    """Main entry point."""
    try:
        await backfill_narrative_actions()
    except KeyboardInterrupt:
        logger.info("\nBackfill interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error during backfill: {e}")
        sys.exit(1)
    finally:
        # Close MongoDB connection
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
