#!/usr/bin/env python3
"""
Comprehensive narrative quality audit script.

Analyzes narratives across multiple dimensions and generates detailed reports.
"""

import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import Dict, List, Any, Tuple
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.crypto_news_aggregator.db.mongodb import mongo_manager
from src.crypto_news_aggregator.services.narrative_themes import calculate_fingerprint_similarity

# Load environment variables
load_dotenv()

# Generic entity list
GENERIC_ENTITIES = [
    'BTC', 'ETH', 'crypto', 'Bitcoin', 'Ethereum', 'blockchain', 
    'market', 'price', 'traders', 'investors', 'Crypto market'
]

# Generic title keywords
GENERIC_TITLE_KEYWORDS = [
    'Activity', 'Updates', 'News', 'Daily', 'Overview', 
    'Movement', 'Comprehensive', 'Spanning'
]

# Generic summary phrases
GENERIC_SUMMARY_PHRASES = [
    'Recent developments', 'General updates', 'Market overview', 
    'Latest news', 'Price movements'
]


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    return title.lower().strip()


def is_generic_entity(nucleus_entity: str) -> bool:
    """Check if nucleus entity is generic."""
    return nucleus_entity in GENERIC_ENTITIES


def is_generic_title(title: str) -> bool:
    """Check if title contains generic keywords or is too short."""
    if not title:
        return True
    
    word_count = len(title.split())
    if word_count < 4:
        return True
    
    for keyword in GENERIC_TITLE_KEYWORDS:
        if keyword.lower() in title.lower():
            return True
    
    return False


def is_generic_summary(summary: str) -> bool:
    """Check if summary contains generic phrases."""
    if not summary:
        return True
    
    for phrase in GENERIC_SUMMARY_PHRASES:
        if phrase.lower() in summary.lower():
            return True
    
    return False


def calculate_title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles using SequenceMatcher."""
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    return SequenceMatcher(None, norm1, norm2).ratio()


def categorize_low_article_count(
    article_count: int, 
    created_at: datetime, 
    now: datetime
) -> Tuple[str, str]:
    """Categorize narratives by article count and age."""
    age_days = (now - created_at).days
    
    if article_count < 3:
        if age_days < 3:
            return "emerging", "MONITOR"
        elif age_days > 7:
            return "failed", "DELETE"
    
    if article_count < 5 and age_days > 14:
        return "stalled", "MERGE or DELETE"
    
    return None, None


def calculate_quality_score(narrative: Dict[str, Any], issues: Dict[str, bool]) -> int:
    """Calculate quality score (0-110) for a narrative."""
    score = 100
    
    if issues.get('generic_both'):
        score -= 40
    elif issues.get('generic'):
        score -= 20
    
    if issues.get('low_count_critical'):
        score -= 20
    
    if issues.get('stale'):
        score -= 20
    
    if issues.get('missing_data'):
        score -= 20
    
    if issues.get('duplicate'):
        score -= 20
    
    article_count = narrative.get('article_count', 0)
    lifecycle_state = narrative.get('lifecycle_state', '')
    if article_count >= 10 and lifecycle_state in ['hot', 'rising']:
        score += 10
    
    return score


async def audit_narratives():
    """Run comprehensive narrative quality audit."""
    
    print("🔍 Starting Narrative Quality Audit...")
    print("=" * 80)
    
    try:
        await mongo_manager.initialize()
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        cursor = narratives_collection.find({})
        narratives = await cursor.to_list(length=None)
        
        now = datetime.now(timezone.utc)
        
        # Run comprehensive analysis
        from audit_analysis import run_full_audit
        run_full_audit(narratives, now)
        
        print("\n✅ Audit complete! Reports generated:")
        print("  - NARRATIVE_QUALITY_AUDIT.md")
        print("  - NARRATIVE_QUALITY_AUDIT.json")
        
    except Exception as e:
        print(f"\n❌ Error during audit: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(audit_narratives())
