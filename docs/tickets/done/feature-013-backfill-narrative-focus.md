ticket-013-backfill-narrative-focus

ContextADR: docs/decisions/004-narrative-focus-identity.md
Sprint: Sprint 2 (Intelligence Layer)
Priority: P0 (URGENT - blocks FEATURE-011)
Estimate: 30-60 minutesBackground:
FEATURE-009 and FEATURE-010 added the narrative_focus field to the narrative detection pipeline and similarity matching logic. However, existing narratives in production (created before 2026-01-06) don't have this field populated. FEATURE-011 (consolidation safety pass) depends on all narratives having a focus field.Scope: Only backfill narratives from December 1, 2025 onwards. Older narratives are less relevant for current operations and can be backfilled later if needed for historical analysis.What to BuildCreate a backfill script that:

Queries narratives missing narrative_focus field (from Dec 1, 2025 onwards)
Uses LLM to extract focus from existing narrative summary
Updates narrative documents with the extracted focus
Logs progress, cost, and any failures
The extraction prompt should match the logic used in FEATURE-009's discover_narrative_from_article() function to ensure consistency.Implementation Guide (Everything You Need)File to Create
CREATE: scripts/backfill_narrative_focus.pyDatabase Schema ReferenceNarrative Document Structure:
python{
  "_id": ObjectId,
  "theme": String,              # "defi", "regulatory", etc.
  "title": String,
  "summary": String,
  "narrative_focus": String,    # THIS IS WHAT WE'RE BACKFILLING
  "entities": [String],
  "article_ids": [ObjectId],
  "article_count": Int,
  "lifecycle_state": String,    # emerging, rising, hot, cooling, dormant
  "timeline_data": [{
    "date": String,
    "article_count": Int,
    "entities": [String],
    "velocity": Float
  }],
  "first_detected_at": DateTime,  # USE THIS FOR DEC 1 FILTER
  "last_updated": DateTime
}LLM Integration PatternModel: Claude 3.5 Haiku (claude-3-5-haiku-20241022)

Cost: $0.80/$4 per 1M tokens (input/output)
Best for extraction tasks
Provider Setup:
pythonfrom crypto_news_aggregator.llm.optimized_anthropic import OptimizedAnthropicProvider
from crypto_news_aggregator.llm.tracking import track_llm_cost

provider = OptimizedAnthropicProvider(api_key=config.anthropic_api_key)Extraction Prompt:
pythonextraction_prompt = f"""Given this narrative summary, extract a 2-5 word phrase describing what is happening (the focus).

Examples:
- "price surge"
- "regulatory enforcement"
- "protocol upgrade"
- "market adoption"
- "security breach"

The focus should capture the ACTION or EVENT, not just the topic.

Summary: {narrative_summary}

Focus phrase (2-5 words):"""MongoDB Connection Patternpythonimport asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client["backdrop"]  # Database name
    
    try:
        await backfill_narrative_focus(db, dry_run=False)
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(main())Implementation Steps1. Query Narratives Needing Backfill:
pythonfrom datetime import datetime, timezone

async def backfill_narrative_focus(db, dry_run=False):
    cutoff_date = datetime(2025, 12, 1, tzinfo=timezone.utc)
    
    query = {
        "narrative_focus": {"$exists": False},
        "first_detected_at": {"$gte": cutoff_date}
    }
    
    narratives = await db.narratives.find(query).to_list(length=None)
    total = len(narratives)
    
    logger.info(f"Found {total} narratives to backfill")
    
    if dry_run:
        logger.info("DRY RUN MODE - showing first 5:")
        for n in narratives[:5]:
            logger.info(f"  - {n['_id']}: {n.get('title', 'N/A')}")
        return2. Extract Focus from Summary:
pythonasync def extract_focus(provider, summary: str) -> str:
    """Extract 2-5 word focus phrase from narrative summary."""
    prompt = f"""Given this narrative summary, extract a 2-5 word phrase describing what is happening (the focus).

Examples:
- "price surge"
- "regulatory enforcement"
- "protocol upgrade"

Summary: {summary}

Focus phrase (2-5 words):"""
    
    response = await provider.generate(
        prompt=prompt,
        max_tokens=50,
        model="claude-3-5-haiku-20241022"
    )
    
    # Clean response
    focus = response.content.strip().strip('"').strip("'")
    return focus3. Batch Processing:
pythonbatch_size = 50
processed = 0
failures = []

for i in range(0, total, batch_size):
    batch = narratives[i:i+batch_size]
    
    # Process concurrently
    tasks = []
    for narrative in batch:
        try:
            task = extract_focus(provider, narrative["summary"])
            tasks.append(task)
        except Exception as e:
            logger.error(f"Error extracting focus for {narrative['_id']}: {e}")
            failures.append(narrative['_id'])
            continue
    
    focuses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Update database
    for narrative, focus in zip(batch, focuses):
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
    
    # Rate limiting
    await asyncio.sleep(0.1)

logger.info(f"Backfill complete: {processed} processed, {len(failures)} failures")4. Cost Tracking:
python# Track after processing
await track_llm_cost(
    db=db,
    model="claude-3-5-haiku-20241022",
    operation="narrative_focus_backfill",
    input_tokens=total_input_tokens,
    output_tokens=total_output_tokens,
    cached=False
)

logger.info(f"Total cost: ${total_cost:.2f}")5. Progress Logging:

Log every 50 narratives: "Processed 50/100 narratives"
Track total cost using llm/tracking.py
Log any failures with narrative_id for manual review
Complete Script Templatepython#!/usr/bin/env python3
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
from datetime import datetime, timezone
from typing import List

from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from crypto_news_aggregator.llm.optimized_anthropic import OptimizedAnthropicProvider
from crypto_news_aggregator.llm.tracking import track_llm_cost


async def extract_focus(provider, summary: str) -> str:
    """Extract 2-5 word focus phrase from narrative summary."""
    # Implementation here
    pass


async def backfill_narrative_focus(db, dry_run=False):
    """Main backfill logic."""
    # Implementation here
    pass


async def main():
    parser = argparse.ArgumentParser(description="Backfill narrative_focus field")
    parser.add_argument("--dry-run", action="store_true", help="Preview without updating DB")
    args = parser.parse_args()
    
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        logger.error("MONGODB_URI not set")
        return
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client["backdrop"]
    
    try:
        await backfill_narrative_focus(db, dry_run=args.dry_run)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())Testing Requirementsbash# From repo root: /Users/mc/dev-projects/crypto-news-aggregator

# 1. Dry run to preview
python scripts/backfill_narrative_focus.py --dry-run

# 2. Real run
python scripts/backfill_narrative_focus.py

# 3. Verify results
python -c "
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from datetime import datetime, timezone

async def check():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client['backdrop']
    
    cutoff = datetime(2025, 12, 1, tzinfo=timezone.utc)
    
    # Count backfilled
    total = await db.narratives.count_documents({
        'narrative_focus': {'$exists': True},
        'first_detected_at': {'$gte': cutoff}
    })
    
    # Count still missing
    missing = await db.narratives.count_documents({
        'narrative_focus': {'$exists': False},
        'first_detected_at': {'$gte': cutoff}
    })
    
    print(f'Backfilled: {total}')
    print(f'Still missing: {missing}')
    
    # Show sample
    sample = await db.narratives.find_one({
        'narrative_focus': {'$exists': True},
        'first_detected_at': {'$gte': cutoff}
    })
    
    if sample:
        print(f\"Sample: {sample.get('title', 'N/A')}\")
        print(f\"Focus: {sample['narrative_focus']}\")
    
    client.close()

asyncio.run(check())
"Test Cases:
python# Test extraction on sample narrative
test_summary = "Bitcoin surges past $100k as institutional demand reaches ATH"
expected_focus = "price surge"  # or similar

# Test batch processing with mock narratives
# Test dry-run mode (no DB writes)
# Test error handling (LLM failures, DB connection issues)Acceptance Criteria
 Script successfully queries narratives missing narrative_focus (from Dec 1, 2025 onwards)
 LLM extracts focus phrases in 2-5 word format
 All narratives from Dec 1, 2025 onwards updated with narrative_focus field
 Narrative fingerprints recalculated to include focus (optional)
 Script logs total narratives processed, cost, and duration
 Zero narratives remain with missing narrative_focus after Dec 1, 2025 cutoff
 Dry-run mode available (preview without updating DB)
Out of Scope
Validating quality of extracted focus (manual spot-check acceptable)
Reprocessing narratives that already have focus
Updating historical timeline_data or article references
Backfilling narratives from before December 1, 2025 (can be done later if needed)
Dependencies
FEATURE-009: COMPLETE ✅ (provides focus extraction pattern)
FEATURE-010: DEPLOYED ✅ (provides similarity logic)
Reference Files (Read Only):

src/crypto_news_aggregator/services/narrative_service.py - LLM patterns
src/crypto_news_aggregator/db/operations/narratives.py - DB operations
src/crypto_news_aggregator/llm/tracking.py - Cost tracking
Success Metrics
All production narratives from Dec 1, 2025 onwards have narrative_focus field populated
Extracted focus phrases follow 2-5 word format
Total cost < $2 (estimated ~$0.02 per narrative for 50-100 narratives)
Zero exceptions during execution
Enables FEATURE-011 implementation to proceed
Environment Variables Required
MONGODB_URI: MongoDB connection string
ANTHROPIC_API_KEY: For LLM calls
Git Workflowbash# Create feature branch (REQUIRED - no direct commits to main)
git checkout -b feature/backfill-narrative-focus

# Add script
git add scripts/backfill_narrative_focus.py

# Commit with proper format
git commit -m "feat(scripts): add narrative focus backfill script

- Backfills narrative_focus for narratives from Dec 1, 2025 onwards
- Uses Claude Haiku for cost-effective extraction
- Processes in batches of 50 with rate limiting
- Includes dry-run mode and cost tracking
- Estimated cost: $1-2 for 50-100 narratives"

# Push and create PR
git push origin feature/backfill-narrative-focusQuick ReferenceDatabase: backdrop (MongoDB Atlas via Motor)
Collection: narratives
Query Filter: {"narrative_focus": {"$exists": False}, "first_detected_at": {"$gte": datetime(2025, 12, 1, tzinfo=timezone.utc)}}
LLM Model: claude-3-5-haiku-20241022
Batch Size: 50 narratives
Rate Limit: 100ms delay between batches
Expected Count: 50-100 narratives
Expected Cost: $1-2
Expected Duration: 5-10 minutes runtime## IMPLEMENTATION COMPLETE (2026-01-07)

**Status:** BLOCKING BUG DISCOVERED - No narratives in database

### What Was Built
✅ Created `scripts/backfill_narrative_focus.py` with:
- MongoDB connection and query for missing narrative_focus
- LLM extraction using Claude Haiku (0.3 temperature)
- Batch processing (50 narratives per batch) with rate limiting
- Cost tracking and progress logging
- Dry-run mode for preview
- Comprehensive error handling

### Script Features
- **LLM Integration:** Direct Anthropic API calls (no dependency on OptimizedAnthropicLLM)
- **Batch Size:** 50 narratives per batch
- **Rate Limiting:** 0.1s delay between batches
- **Cost Tracking:** Monitors input/output tokens and estimated cost
- **Error Handling:** Tracks failures and logs narrative IDs for manual review
- **Dry-run Mode:** Preview narratives without updating database

### Testing Results
✅ Syntax validation: Script compiles without errors
✅ Dry-run test: Executed successfully with --dry-run flag
✅ Environment loading: Correctly reads MONGODB_URI and ANTHROPIC_API_KEY

### Critical Issue Discovered

**Problem:** Database appears empty - 0 narratives exist
```
Total narratives: 0
With narrative_focus: 0
Missing narrative_focus: 0
```

**Impact:** Cannot verify backfill script works in practice. Blocks FEATURE-011 implementation.

**Root Cause:** Unknown - need to investigate:
1. Is the article ingestion pipeline running?
2. Are articles being ingested but narratives not being detected?
3. Is there a bug in narrative detection that broke between FEATURE-010 deployment and now?

### Next Steps
1. **Investigate missing narratives** (BLOCKING)
   - Check RSS fetcher status
   - Verify articles are being ingested
   - Check narrative detection logs
   - Review recent commits for any breaking changes

2. **Once narratives exist:**
   - Run: `poetry run python scripts/backfill_narrative_focus.py --dry-run`
   - Review sample narratives and extracted focus phrases
   - Run: `poetry run python scripts/backfill_narrative_focus.py` (real execution)
   - Verify all narratives have narrative_focus field post-backfill

3. **Then proceed to FEATURE-011**
   - Post-detection consolidation safety pass
   - Depends on: all narratives having narrative_focus field

### Files
- **Created:** `scripts/backfill_narrative_focus.py` (201 lines)
- **Ready for:** Dry-run testing once narratives exist


