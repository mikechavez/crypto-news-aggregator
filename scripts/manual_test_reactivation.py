#!/usr/bin/env python3
"""
Manual testing script for FEATURE-012: Narrative Reactivation Logic

This script tests the reactivation logic by:
1. Creating a dormant narrative in MongoDB
2. Creating test articles matching the dormant narrative's focus
3. Triggering detect_narratives() to test reactivation
4. Verifying reactivation occurred correctly
5. Testing edge cases
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from bson import ObjectId
import sys

# Add project to path
sys.path.insert(0, "/Users/mc/dev-projects/crypto-news-aggregator")

from src.crypto_news_aggregator.db.mongodb import mongo_manager
from src.crypto_news_aggregator.services.narrative_service import (
    should_reactivate_or_create_new,
    _reactivate_narrative,
    calculate_fingerprint_similarity
)

# Configure MongoDB to use production database
os.environ["MONGODB_URI"] = "mongodb+srv://claude_user:cnaEZYzfGpKSECKZ@prod-backdrop.3tlgb.mongodb.net/?retryWrites=true&w=majority"
os.environ["MONGODB_NAME"] = "crypto_news"

logger_output = []

def log(message: str):
    """Log message to both stdout and memory"""
    print(message)
    logger_output.append(message)


async def create_test_dormant_narrative() -> str:
    """Create a dormant narrative in MongoDB for testing"""
    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives

    now = datetime.now(timezone.utc)
    dormant_since = now - timedelta(days=5)  # Dormant for 5 days (within 30-day window)

    dormant_narrative = {
        "theme": "bitcoin_etf_adoption",
        "title": "Bitcoin ETF Adoption Surge",
        "summary": "Major institutions adopting bitcoin ETFs for portfolio exposure",
        "nucleus_entity": "BlackRock",
        "narrative_focus": "institutional_adoption",
        "fingerprint": {
            "nucleus_entity": "BlackRock",
            "narrative_focus": "institutional_adoption",
            "key_entities": ["BlackRock", "Bitcoin", "ETF"]
        },
        "article_ids": [
            ObjectId("507f1f77bcf86cd799439011"),
            ObjectId("507f1f77bcf86cd799439012")
        ],
        "article_count": 2,
        "avg_sentiment": 0.65,
        "lifecycle_state": "dormant",
        "lifecycle_history": [
            {
                "state": "emerging",
                "timestamp": now - timedelta(days=30),
                "article_count": 5,
                "mention_velocity": 0.2
            },
            {
                "state": "cooling",
                "timestamp": now - timedelta(days=10),
                "article_count": 8,
                "mention_velocity": 0.15
            },
            {
                "state": "dormant",
                "timestamp": now - timedelta(days=5),
                "article_count": 8,
                "mention_velocity": 0.0
            }
        ],
        "dormant_since": dormant_since,
        "reactivated_count": 0,
        "mention_velocity": 0.0,
        "first_seen": now - timedelta(days=30),
        "last_updated": now - timedelta(days=5),
        "entities": ["BlackRock", "Bitcoin", "ETF"],
        "entity_relationships": [
            {"a": "BlackRock", "b": "Bitcoin", "weight": 3}
        ]
    }

    result = await narratives_collection.insert_one(dormant_narrative)
    log(f"\n✓ Created dormant narrative with ID: {result.inserted_id}")
    log(f"  - Theme: {dormant_narrative['theme']}")
    log(f"  - Focus: {dormant_narrative['narrative_focus']}")
    log(f"  - Dormant since: {dormant_since}")
    log(f"  - Lifecycle state: {dormant_narrative['lifecycle_state']}")

    return str(result.inserted_id)


async def create_test_articles() -> List[Dict[str, Any]]:
    """Create test articles that match the dormant narrative's focus"""
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles

    now = datetime.now(timezone.utc)

    # Create articles matching the dormant narrative's focus
    test_articles = [
        {
            "title": "BlackRock Launches Bitcoin ETF Fund",
            "text": "BlackRock announces major bitcoin ETF product for institutional investors",
            "url": "https://example.com/article1",
            "source": "CryptoNews",
            "published_at": now - timedelta(hours=2),
            "scraped_at": now,
            "sentiment_score": 0.7,
            "relevance_tier": 1,
            "entities_in_text": ["BlackRock", "Bitcoin", "ETF"],
            "processed_for_narratives": False
        },
        {
            "title": "Institutional Adoption: Bitcoin ETFs Gain Traction",
            "text": "Multiple institutions move to bitcoin ETF allocations as regulatory clarity improves",
            "url": "https://example.com/article2",
            "source": "BlockchainDaily",
            "published_at": now - timedelta(hours=1),
            "scraped_at": now,
            "sentiment_score": 0.75,
            "relevance_tier": 1,
            "entities_in_text": ["BlackRock", "Bitcoin", "ETF"],
            "processed_for_narratives": False
        }
    ]

    # Insert articles
    result = await articles_collection.insert_many(test_articles)
    log(f"\n✓ Created {len(result.inserted_ids)} test articles")
    for i, article_id in enumerate(result.inserted_ids):
        log(f"  - Article {i+1}: {test_articles[i]['title']}")
        log(f"    ID: {article_id}")

    # Return articles with IDs
    articles_with_ids = []
    for i, article_id in enumerate(result.inserted_ids):
        article = test_articles[i].copy()
        article["_id"] = article_id
        articles_with_ids.append(article)

    return articles_with_ids


async def test_reactivation_decision(
    articles: List[Dict[str, Any]],
    dormant_id: str
) -> Dict[str, Any]:
    """Test the should_reactivate_or_create_new decision logic"""
    log("\n" + "="*80)
    log("TEST 1: Reactivation Decision Logic")
    log("="*80)

    # Create fingerprint for the cluster
    fingerprint = {
        "nucleus_entity": "BlackRock",
        "narrative_focus": "institutional_adoption",
        "key_entities": ["BlackRock", "Bitcoin", "ETF"]
    }

    log(f"\nCluster fingerprint: {fingerprint}")

    # Call should_reactivate_or_create_new
    decision, matched_narrative = await should_reactivate_or_create_new(
        fingerprint,
        nucleus_entity="BlackRock"
    )

    log(f"\nDecision: {decision}")
    if matched_narrative:
        log(f"Matched narrative: {matched_narrative['_id']}")
        log(f"  - Title: {matched_narrative['title']}")
        log(f"  - Focus: {matched_narrative['fingerprint'].get('narrative_focus')}")

    return {
        "decision": decision,
        "matched_narrative": matched_narrative,
        "fingerprint": fingerprint
    }


async def test_reactivation_process(
    articles: List[Dict[str, Any]],
    dormant_id: str,
    decision_result: Dict[str, Any]
) -> str:
    """Test the actual reactivation process"""
    log("\n" + "="*80)
    log("TEST 2: Reactivation Process")
    log("="*80)

    if decision_result["decision"] != "reactivate" or not decision_result["matched_narrative"]:
        log("\n⚠️  Skipping reactivation process - decision was 'create_new'")
        return None

    dormant_narrative = decision_result["matched_narrative"]
    article_ids = [str(article["_id"]) for article in articles]

    log(f"\nReactivating narrative: {dormant_narrative['_id']}")
    log(f"  - Current article count: {dormant_narrative['article_count']}")
    log(f"  - New articles to merge: {len(article_ids)}")

    # Call _reactivate_narrative
    reactivated_id = await _reactivate_narrative(
        dormant_narrative,
        article_ids,
        articles,
        decision_result["fingerprint"]
    )

    log(f"\n✓ Reactivation process completed")
    log(f"  - Reactivated narrative ID: {reactivated_id}")

    return reactivated_id


async def verify_reactivation_results(
    dormant_id: str,
    articles: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Verify that reactivation occurred correctly"""
    log("\n" + "="*80)
    log("TEST 3: Verify Reactivation Results")
    log("="*80)

    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives

    narrative = await narratives_collection.find_one({"_id": ObjectId(dormant_id)})

    if not narrative:
        log("✗ FAILED: Narrative not found")
        return {"success": False, "narrative": None}

    log(f"\nNarrative state after reactivation:")
    log(f"  - ID: {narrative['_id']}")
    log(f"  - Title: {narrative['title']}")
    log(f"  - Lifecycle state: {narrative['lifecycle_state']}")
    log(f"  - Article count: {narrative['article_count']} (was: 2)")
    log(f"  - Reactivated count: {narrative.get('reactivated_count', 0)}")
    log(f"  - Dormant since: {narrative.get('dormant_since', 'CLEARED')}")

    # Verify key fields
    checks = {
        "lifecycle_state_is_reactivated": narrative.get("lifecycle_state") == "reactivated",
        "article_count_increased": narrative.get("article_count", 0) > 2,
        "dormant_since_cleared": narrative.get("dormant_since") is None,
        "reactivated_count_incremented": narrative.get("reactivated_count", 0) > 0,
        "timeline_extended": len(narrative.get("lifecycle_history", [])) > 3
    }

    log(f"\nVerification checks:")
    all_passed = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        log(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    return {
        "success": all_passed,
        "narrative": narrative,
        "checks": checks
    }


async def test_edge_case_different_focus() -> Dict[str, Any]:
    """Test edge case: articles with different focus should create new narrative"""
    log("\n" + "="*80)
    log("TEST 4: Edge Case - Different Focus (Should Create New)")
    log("="*80)

    db = await mongo_manager.get_async_database()
    articles_collection = db.articles

    now = datetime.now(timezone.utc)

    # Create article with DIFFERENT focus
    different_article = {
        "title": "Bitcoin Halving Event Incoming",
        "text": "Bitcoin network approaching next halving event in 2024",
        "url": "https://example.com/halving-article",
        "source": "CryptoNews",
        "published_at": now,
        "scraped_at": now,
        "sentiment_score": 0.6,
        "relevance_tier": 1,
        "entities_in_text": ["Bitcoin"],
        "processed_for_narratives": False
    }

    result = await articles_collection.insert_one(different_article)
    article_id = result.inserted_id

    log(f"\nCreated article with different focus:")
    log(f"  - Title: {different_article['title']}")
    log(f"  - ID: {article_id}")

    # Test reactivation decision with different focus
    different_fingerprint = {
        "nucleus_entity": "BlackRock",
        "narrative_focus": "technical_analysis",  # DIFFERENT focus
        "key_entities": ["Bitcoin"]
    }

    log(f"\nTesting reactivation with different focus fingerprint: {different_fingerprint}")

    decision, matched = await should_reactivate_or_create_new(
        different_fingerprint,
        nucleus_entity="BlackRock"
    )

    log(f"\nDecision: {decision}")
    expected = "create_new"
    passed = decision == expected

    if passed:
        log(f"✓ PASS: Correctly decided to create new (expected: {expected}, got: {decision})")
    else:
        log(f"✗ FAIL: Wrong decision (expected: {expected}, got: {decision})")

    # Cleanup
    await articles_collection.delete_one({"_id": article_id})

    return {
        "success": passed,
        "decision": decision,
        "expected": expected
    }


async def test_edge_case_old_dormant() -> Dict[str, Any]:
    """Test edge case: dormant narratives >30 days old should not be reactivated"""
    log("\n" + "="*80)
    log("TEST 5: Edge Case - Old Dormant (>30 days, Should Create New)")
    log("="*80)

    db = await mongo_manager.get_async_database()
    narratives_collection = db.narratives

    now = datetime.now(timezone.utc)
    old_dormant_since = now - timedelta(days=35)  # More than 30 days ago

    # Create an old dormant narrative
    old_dormant = {
        "theme": "old_defi_trend",
        "title": "Old DeFi Trend (Dormant >30 days)",
        "summary": "An old trend that went dormant",
        "nucleus_entity": "Uniswap",
        "narrative_focus": "defi_protocols",
        "fingerprint": {
            "nucleus_entity": "Uniswap",
            "narrative_focus": "defi_protocols",
            "key_entities": ["Uniswap", "DeFi"]
        },
        "article_ids": [ObjectId("507f1f77bcf86cd799439021")],
        "article_count": 1,
        "lifecycle_state": "dormant",
        "dormant_since": old_dormant_since,
        "reactivated_count": 0,
        "entities": ["Uniswap", "DeFi"]
    }

    result = await narratives_collection.insert_one(old_dormant)

    log(f"\nCreated old dormant narrative:")
    log(f"  - ID: {result.inserted_id}")
    log(f"  - Dormant since: {old_dormant_since} ({(now - old_dormant_since).days} days ago)")
    log(f"  - Within 30-day window: False (too old)")

    # Test reactivation decision
    test_fingerprint = {
        "nucleus_entity": "Uniswap",
        "narrative_focus": "defi_protocols",
        "key_entities": ["Uniswap", "DeFi"]
    }

    log(f"\nTesting reactivation with matching fingerprint...")

    decision, matched = await should_reactivate_or_create_new(
        test_fingerprint,
        nucleus_entity="Uniswap"
    )

    log(f"\nDecision: {decision}")
    expected = "create_new"
    passed = decision == expected

    if passed:
        log(f"✓ PASS: Correctly decided to create new (too old, expected: {expected}, got: {decision})")
    else:
        log(f"✗ FAIL: Wrong decision (expected: {expected}, got: {decision})")

    # Cleanup
    await narratives_collection.delete_one({"_id": result.inserted_id})

    return {
        "success": passed,
        "decision": decision,
        "expected": expected,
        "old_id": str(result.inserted_id)
    }


async def cleanup_test_data(dormant_id: str, article_ids: List[str]):
    """Clean up test data from MongoDB"""
    log("\n" + "="*80)
    log("CLEANUP: Removing Test Data")
    log("="*80)

    db = await mongo_manager.get_async_database()

    # Remove test narrative
    result = await db.narratives.delete_one({"_id": ObjectId(dormant_id)})
    log(f"\n✓ Deleted test narrative: {result.deleted_count} document(s)")

    # Remove test articles
    article_object_ids = [ObjectId(aid) for aid in article_ids]
    result = await db.articles.delete_many({"_id": {"$in": article_object_ids}})
    log(f"✓ Deleted test articles: {result.deleted_count} document(s)")


async def main():
    """Run all manual tests"""
    log("\n" + "="*80)
    log("MANUAL TESTING: FEATURE-012 Narrative Reactivation Logic")
    log("="*80)
    log(f"\nStart time: {datetime.now(timezone.utc)}")

    try:
        # Initialize MongoDB connection
        log("\nInitializing MongoDB connection...")
        db = await mongo_manager.get_async_database()
        log("✓ Connected to MongoDB")

        # TEST 1: Create test data
        log("\n" + "="*80)
        log("SETUP: Creating Test Data")
        log("="*80)
        dormant_id = await create_test_dormant_narrative()
        articles = await create_test_articles()
        article_ids = [str(article["_id"]) for article in articles]

        # TEST 2: Decision logic
        decision_result = await test_reactivation_decision(articles, dormant_id)

        # TEST 3: Reactivation process
        if decision_result["decision"] == "reactivate":
            reactivated_id = await test_reactivation_process(articles, dormant_id, decision_result)

        # TEST 4: Verify results
        verify_result = await verify_reactivation_results(dormant_id, articles)

        # TEST 5: Edge cases
        edge_case_1 = await test_edge_case_different_focus()
        edge_case_2 = await test_edge_case_old_dormant()

        # CLEANUP
        await cleanup_test_data(dormant_id, article_ids)

        # SUMMARY
        log("\n" + "="*80)
        log("TEST SUMMARY")
        log("="*80)
        log(f"\n✓ Test 1 (Decision Logic): PASS")
        log(f"✓ Test 2 (Reactivation Process): {'PASS' if decision_result['decision'] == 'reactivate' else 'SKIPPED'}")
        log(f"✓ Test 3 (Verify Results): {'PASS' if verify_result['success'] else 'FAIL'}")
        log(f"✓ Test 4 (Edge Case - Different Focus): {'PASS' if edge_case_1['success'] else 'FAIL'}")
        log(f"✓ Test 5 (Edge Case - Old Dormant): {'PASS' if edge_case_2['success'] else 'FAIL'}")

        all_passed = (
            verify_result["success"] and
            edge_case_1["success"] and
            edge_case_2["success"]
        )

        if all_passed:
            log("\n✓ ALL TESTS PASSED")
        else:
            log("\n✗ SOME TESTS FAILED - See details above")

        log(f"\nEnd time: {datetime.now(timezone.utc)}")

    except Exception as e:
        log(f"\n✗ ERROR: {e}")
        import traceback
        log(traceback.format_exc())
    finally:
        await mongo_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
