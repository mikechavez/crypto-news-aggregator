#!/usr/bin/env python3
"""
Backfill narrative_focus field for narratives from December 1, 2025 onwards.

Usage:
    python scripts/backfill_narrative_focus.py              # Real run
    python scripts/backfill_narrative_focus.py --dry-run    # Preview only
"""

import asyncio
import os
import sys
import argparse
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from collections import Counter

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger

# Load environment variables from .env
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


# Configure logger
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


class NarrativeFocusBackfiller:
    """Handles backfilling narrative_focus field for existing narratives."""

    HAIKU_MODEL = "claude-3-5-haiku-20241022"
    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str):
        """Initialize the backfiller with Anthropic API key."""
        if not api_key:
            raise ValueError("Anthropic API key not provided")
        self.api_key = api_key
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    def _make_api_call(self, prompt: str, max_tokens: int = 100) -> Dict[str, Any]:
        """
        Make synchronous API call to Anthropic.

        Returns:
            Dict with 'content' (text response), 'input_tokens', and 'output_tokens'
        """
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.HAIKU_MODEL,
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            with httpx.Client() as client:
                response = client.post(
                    self.API_URL, headers=headers, json=payload, timeout=30
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "content": data.get("content", [{}])[0].get("text", ""),
                    "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("output_tokens", 0),
                }
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Anthropic API request failed with status {e.response.status_code}: {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    async def extract_focus(self, summary: str) -> str:
        """Extract 2-5 word focus phrase from narrative summary."""
        prompt = f"""Given this narrative summary, extract a 2-5 word phrase describing what is happening (the focus).

Examples:
- "price surge"
- "regulatory enforcement"
- "protocol upgrade"
- "market adoption"
- "security breach"

The focus should capture the ACTION or EVENT, not just the topic.

Summary: {summary}

Focus phrase (2-5 words):"""

        response = self._make_api_call(prompt, max_tokens=50)

        # Track tokens
        self.total_input_tokens += response["input_tokens"]
        self.total_output_tokens += response["output_tokens"]

        # Clean response
        focus = response["content"].strip().strip('"').strip("'")
        return focus

    async def backfill_narrative_focus(self, db, dry_run: bool = False):
        """Main backfill logic."""
        # Backfill ALL narratives missing narrative_focus field
        query = {
            "narrative_focus": {"$exists": False}
        }

        narratives = await db.narratives.find(query).to_list(length=None)
        total = len(narratives)

        logger.info(f"Found {total} narratives to backfill")

        if dry_run:
            logger.info("DRY RUN MODE - showing first 5:")
            for n in narratives[:5]:
                logger.info(f"  - {n['_id']}: {n.get('title', 'N/A')}")
            return

        batch_size = 50
        processed = 0
        failures = []

        for i in range(0, total, batch_size):
            batch = narratives[i:i + batch_size]

            # Process concurrently
            tasks = []
            batch_start_idx = i

            for idx, narrative in enumerate(batch):
                try:
                    task = self.extract_focus(narrative["summary"])
                    tasks.append((idx, task))
                except Exception as e:
                    logger.error(f"Error extracting focus for {narrative['_id']}: {e}")
                    failures.append(narrative['_id'])
                    continue

            # Gather results
            if tasks:
                results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

                # Update database
                for (idx, _), focus in zip(tasks, results):
                    narrative = batch[idx]

                    if isinstance(focus, Exception):
                        logger.error(f"Failed to extract for {narrative['_id']}: {focus}")
                        failures.append(narrative['_id'])
                        continue

                    await db.narratives.update_one(
                        {"_id": narrative["_id"]},
                        {"$set": {"narrative_focus": focus}}
                    )

            processed += len(batch)
            logger.info(f"Processed {processed}/{total} narratives")

            # Rate limiting to be respectful to API
            if i + batch_size < total:
                await asyncio.sleep(0.1)

        # Calculate cost
        # Haiku: $0.80 per 1M input tokens, $4 per 1M output tokens
        input_cost = (self.total_input_tokens / 1_000_000) * 0.80
        output_cost = (self.total_output_tokens / 1_000_000) * 4.00
        self.total_cost = input_cost + output_cost

        logger.info(f"\n{'='*60}")
        logger.info(f"Backfill Complete")
        logger.info(f"{'='*60}")
        logger.info(f"Total processed: {processed}")
        logger.info(f"Total failures: {len(failures)}")
        logger.info(f"Input tokens: {self.total_input_tokens}")
        logger.info(f"Output tokens: {self.total_output_tokens}")
        logger.info(f"Estimated cost: ${self.total_cost:.2f}")

        if failures:
            logger.warning(f"Failed narrative IDs: {failures}")


async def main():
    parser = argparse.ArgumentParser(description="Backfill narrative_focus field")
    parser.add_argument("--dry-run", action="store_true", help="Preview without updating DB")
    args = parser.parse_args()

    # Validate environment
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        logger.error("MONGODB_URI not set")
        sys.exit(1)

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Connect to MongoDB
    client = AsyncIOMotorClient(mongo_uri)
    db = client["crypto_news"]

    try:
        backfiller = NarrativeFocusBackfiller(api_key=anthropic_key)
        await backfiller.backfill_narrative_focus(db, dry_run=args.dry_run)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
