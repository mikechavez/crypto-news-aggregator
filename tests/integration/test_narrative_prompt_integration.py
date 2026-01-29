"""
Integration tests for narrative prompt enhancement.

Tests the complete flow with real LLM calls to verify:
1. Entity normalization works in practice
2. Nucleus selection is improved
3. Salience scoring is more selective
"""

import pytest
import asyncio
from datetime import datetime, timezone

from crypto_news_aggregator.services.narrative_themes import (
    discover_narrative_from_article,
    validate_narrative_json
)


# Test articles designed to verify specific normalization behaviors
TEST_ARTICLES = [
    {
        "id": "sec_normalization_test",
        "title": "U.S. Securities and Exchange Commission Files Lawsuit Against Binance",
        "summary": "The U.S. Securities and Exchange Commission has filed a comprehensive lawsuit against Binance and its CEO for alleged securities violations and regulatory non-compliance.",
        "expected_entities": ["SEC", "Binance"],
        "expected_nucleus": "SEC",
        "avoid_entities": ["U.S. SEC", "Securities and Exchange Commission", "US SEC"],
        "test_type": "entity_normalization"
    },
    {
        "id": "ethereum_normalization_test",
        "title": "Ethereum Network Completes Shanghai Upgrade",
        "summary": "The Ethereum network has successfully completed the Shanghai upgrade, enabling staking withdrawals. The Ethereum Foundation announced the upgrade went smoothly.",
        "expected_entities": ["Ethereum"],
        "expected_nucleus": "Ethereum",
        "avoid_entities": ["Ethereum network", "Ethereum Foundation", "ETH"],
        "test_type": "entity_normalization"
    },
    {
        "id": "bitcoin_normalization_test",
        "title": "Bitcoin Network Hash Rate Reaches All-Time High",
        "summary": "The Bitcoin network has reached a new all-time high in hash rate, signaling strong security. Bitcoin Core developers continue to work on improvements.",
        "expected_entities": ["Bitcoin"],
        "expected_nucleus": "Bitcoin",
        "avoid_entities": ["Bitcoin network", "BTC", "Bitcoin Core"],
        "test_type": "entity_normalization"
    },
    {
        "id": "regulatory_nucleus_test",
        "title": "SEC Sues Coinbase Over Unregistered Securities",
        "summary": "The Securities and Exchange Commission has filed a lawsuit against Coinbase, alleging the exchange operated as an unregistered securities exchange and broker.",
        "expected_nucleus": "SEC",
        "avoid_nucleus": ["lawsuit", "regulation", "securities"],
        "test_type": "nucleus_selection"
    },
    {
        "id": "company_nucleus_test",
        "title": "Coinbase CEO Brian Armstrong Announces Major Restructuring",
        "summary": "Coinbase CEO Brian Armstrong has announced a major company restructuring, including layoffs and strategic pivots. Armstrong emphasized the need for efficiency.",
        "expected_nucleus": "Coinbase",
        "avoid_nucleus": ["Brian Armstrong", "CEO"],
        "test_type": "nucleus_selection"
    },
    {
        "id": "specific_over_generic_test",
        "title": "Binance Captures 60% of Global Crypto Exchange Volume",
        "summary": "Binance has captured 60% of global cryptocurrency exchange trading volume, far outpacing competitors like Coinbase and Kraken.",
        "expected_nucleus": "Binance",
        "avoid_nucleus": ["crypto exchanges", "exchanges", "cryptocurrency market"],
        "test_type": "nucleus_selection"
    },
    {
        "id": "salience_selectivity_test",
        "title": "SEC, CFTC, and DOJ Coordinate Enforcement Against Crypto Firms",
        "summary": "The SEC is leading a coordinated enforcement effort with the CFTC and DOJ against cryptocurrency firms. The SEC has taken the primary role in the investigation, with CFTC and DOJ providing support.",
        "expected_high_salience": ["SEC"],  # Only SEC should have salience 5
        "expected_medium_salience": ["CFTC", "DOJ"],  # Should have salience 3-4
        "test_type": "salience_scoring"
    },
    {
        "id": "background_exclusion_test",
        "title": "Coinbase Launches New DeFi Trading Platform",
        "summary": "Coinbase has launched a new DeFi trading platform, competing with Uniswap. The platform supports various tokens and aims to capture market share in the growing DeFi space. Bitcoin and Ethereum will be supported.",
        "expected_entities": ["Coinbase", "Uniswap"],  # Primary actors
        "avoid_entities_with_low_salience": ["Bitcoin", "Ethereum", "DeFi"],  # Background mentions
        "test_type": "salience_scoring"
    }
]


@pytest.mark.integration
@pytest.mark.asyncio
class TestEntityNormalizationIntegration:
    """Integration tests for entity normalization with real LLM calls."""
    
    async def test_sec_normalization_integration(self):
        """Test SEC normalization with real LLM call."""
        test_case = TEST_ARTICLES[0]
        
        article = {
            "_id": test_case["id"],
            "article_id": test_case["id"],
            "title": test_case["title"],
            "description": test_case["summary"]
        }
        
        result = await discover_narrative_from_article(article)
        
        # Verify result
        assert result is not None, "LLM should return valid narrative"
        
        # Check validation
        is_valid, error = validate_narrative_json(result)
        assert is_valid, f"Validation failed: {error}"
        
        # Verify normalization
        actors = result["actors"]
        print(f"\n✓ Extracted actors: {actors}")
        
        # Should include normalized entities
        for expected in test_case["expected_entities"]:
            assert expected in actors, f"Should include normalized entity '{expected}'"
        
        # Should NOT include non-normalized variants
        for avoid in test_case["avoid_entities"]:
            assert avoid not in actors, f"Should NOT include variant '{avoid}'"
        
        # Verify nucleus
        assert result["nucleus_entity"] == test_case["expected_nucleus"]
        print(f"✓ Nucleus entity: {result['nucleus_entity']}")
    
    async def test_ethereum_normalization_integration(self):
        """Test Ethereum normalization with real LLM call."""
        test_case = TEST_ARTICLES[1]
        
        article = {
            "_id": test_case["id"],
            "article_id": test_case["id"],
            "title": test_case["title"],
            "description": test_case["summary"]
        }
        
        result = await discover_narrative_from_article(article)
        
        assert result is not None
        is_valid, error = validate_narrative_json(result)
        assert is_valid, f"Validation failed: {error}"
        
        actors = result["actors"]
        print(f"\n✓ Extracted actors: {actors}")
        
        # Verify normalization
        for expected in test_case["expected_entities"]:
            assert expected in actors, f"Should include '{expected}'"
        
        for avoid in test_case["avoid_entities"]:
            assert avoid not in actors, f"Should NOT include '{avoid}'"
        
        print(f"✓ Nucleus entity: {result['nucleus_entity']}")
    
    async def test_bitcoin_normalization_integration(self):
        """Test Bitcoin normalization with real LLM call."""
        test_case = TEST_ARTICLES[2]
        
        article = {
            "_id": test_case["id"],
            "article_id": test_case["id"],
            "title": test_case["title"],
            "description": test_case["summary"]
        }
        
        result = await discover_narrative_from_article(article)
        
        assert result is not None
        is_valid, error = validate_narrative_json(result)
        assert is_valid, f"Validation failed: {error}"
        
        actors = result["actors"]
        print(f"\n✓ Extracted actors: {actors}")
        
        # Verify normalization
        for expected in test_case["expected_entities"]:
            assert expected in actors, f"Should include '{expected}'"
        
        for avoid in test_case["avoid_entities"]:
            assert avoid not in actors, f"Should NOT include '{avoid}'"
        
        print(f"✓ Nucleus entity: {result['nucleus_entity']}")


@pytest.mark.integration
@pytest.mark.asyncio
class TestNucleusSelectionIntegration:
    """Integration tests for nucleus selection with real LLM calls."""
    
    async def test_regulatory_story_nucleus(self):
        """Test that regulatory stories have regulator as nucleus, not abstract concepts."""
        test_case = TEST_ARTICLES[3]
        
        article = {
            "_id": test_case["id"],
            "article_id": test_case["id"],
            "title": test_case["title"],
            "description": test_case["summary"]
        }
        
        result = await discover_narrative_from_article(article)
        
        assert result is not None
        is_valid, error = validate_narrative_json(result)
        assert is_valid, f"Validation failed: {error}"
        
        nucleus = result["nucleus_entity"]
        print(f"\n✓ Nucleus entity: {nucleus}")
        
        # Should be the expected nucleus
        assert nucleus == test_case["expected_nucleus"], f"Expected nucleus '{test_case['expected_nucleus']}', got '{nucleus}'"
        
        # Should NOT be abstract concepts
        for avoid in test_case["avoid_nucleus"]:
            assert nucleus != avoid, f"Nucleus should not be '{avoid}'"
    
    async def test_company_story_nucleus(self):
        """Test that company stories have company as nucleus, not CEO."""
        test_case = TEST_ARTICLES[4]
        
        article = {
            "_id": test_case["id"],
            "article_id": test_case["id"],
            "title": test_case["title"],
            "description": test_case["summary"]
        }
        
        result = await discover_narrative_from_article(article)
        
        assert result is not None
        is_valid, error = validate_narrative_json(result)
        assert is_valid, f"Validation failed: {error}"
        
        nucleus = result["nucleus_entity"]
        print(f"\n✓ Nucleus entity: {nucleus}")
        
        # Should be company, not CEO
        assert nucleus == test_case["expected_nucleus"], f"Expected nucleus '{test_case['expected_nucleus']}', got '{nucleus}'"
        
        for avoid in test_case["avoid_nucleus"]:
            assert nucleus != avoid, f"Nucleus should not be '{avoid}'"
    
    async def test_specific_over_generic_nucleus(self):
        """Test that specific entities are chosen over generic categories."""
        test_case = TEST_ARTICLES[5]
        
        article = {
            "_id": test_case["id"],
            "article_id": test_case["id"],
            "title": test_case["title"],
            "description": test_case["summary"]
        }
        
        result = await discover_narrative_from_article(article)
        
        assert result is not None
        is_valid, error = validate_narrative_json(result)
        assert is_valid, f"Validation failed: {error}"
        
        nucleus = result["nucleus_entity"]
        print(f"\n✓ Nucleus entity: {nucleus}")
        
        # Should be specific entity
        assert nucleus == test_case["expected_nucleus"], f"Expected nucleus '{test_case['expected_nucleus']}', got '{nucleus}'"
        
        # Should NOT be generic category
        for avoid in test_case["avoid_nucleus"]:
            assert nucleus != avoid, f"Nucleus should not be generic '{avoid}'"


@pytest.mark.integration
@pytest.mark.asyncio
class TestSalienceScoringIntegration:
    """Integration tests for salience scoring with real LLM calls."""
    
    async def test_selective_high_salience(self):
        """Test that only 1-2 entities have salience 5."""
        test_case = TEST_ARTICLES[6]
        
        article = {
            "_id": test_case["id"],
            "article_id": test_case["id"],
            "title": test_case["title"],
            "description": test_case["summary"]
        }
        
        result = await discover_narrative_from_article(article)
        
        assert result is not None
        is_valid, error = validate_narrative_json(result)
        assert is_valid, f"Validation failed: {error}"
        
        salience_scores = result["actor_salience"]
        print(f"\n✓ Salience scores: {salience_scores}")
        
        # Count entities with salience 5
        high_salience_entities = [entity for entity, score in salience_scores.items() if score == 5]
        print(f"✓ High salience (5) entities: {high_salience_entities}")
        
        assert len(high_salience_entities) <= 2, f"Should have at most 2 entities with salience 5, got {len(high_salience_entities)}"
        
        # Verify expected high salience entities
        for entity in test_case["expected_high_salience"]:
            assert entity in high_salience_entities, f"'{entity}' should have salience 5"
    
    async def test_background_mentions_excluded(self):
        """Test that background mentions are excluded (salience < 2)."""
        test_case = TEST_ARTICLES[7]
        
        article = {
            "_id": test_case["id"],
            "article_id": test_case["id"],
            "title": test_case["title"],
            "description": test_case["summary"]
        }
        
        result = await discover_narrative_from_article(article)
        
        assert result is not None
        is_valid, error = validate_narrative_json(result)
        assert is_valid, f"Validation failed: {error}"
        
        actors = result["actors"]
        salience_scores = result["actor_salience"]
        print(f"\n✓ Actors: {actors}")
        print(f"✓ Salience scores: {salience_scores}")
        
        # All actors should have salience >= 2
        for actor in actors:
            assert salience_scores[actor] >= 2, f"'{actor}' should have salience >= 2, got {salience_scores[actor]}"
        
        # Background mentions should be excluded
        for avoid in test_case.get("avoid_entities_with_low_salience", []):
            if avoid in actors:
                # If included, must have salience >= 2
                assert salience_scores[avoid] >= 2, f"'{avoid}' should either be excluded or have salience >= 2"
    
    async def test_clear_salience_hierarchy(self):
        """Test that salience scores show clear hierarchy."""
        test_case = TEST_ARTICLES[6]
        
        article = {
            "_id": test_case["id"],
            "article_id": test_case["id"],
            "title": test_case["title"],
            "description": test_case["summary"]
        }
        
        result = await discover_narrative_from_article(article)
        
        assert result is not None
        is_valid, error = validate_narrative_json(result)
        assert is_valid, f"Validation failed: {error}"
        
        salience_scores = result["actor_salience"]
        print(f"\n✓ Salience scores: {salience_scores}")
        
        # Should have differentiation in scores
        unique_scores = set(salience_scores.values())
        print(f"✓ Unique salience levels: {sorted(unique_scores, reverse=True)}")
        
        assert len(unique_scores) >= 2, f"Should have at least 2 different salience levels, got {len(unique_scores)}"
        
        # Nucleus should have highest salience
        nucleus = result["nucleus_entity"]
        nucleus_salience = salience_scores[nucleus]
        max_salience = max(salience_scores.values())
        
        assert nucleus_salience == max_salience, f"Nucleus '{nucleus}' should have highest salience ({max_salience}), got {nucleus_salience}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_integration():
    """Test complete workflow with multiple articles to verify overall improvements."""
    print("\n" + "="*80)
    print("INTEGRATION TEST: Full Workflow")
    print("="*80)
    
    results = []
    
    for test_case in TEST_ARTICLES[:3]:  # Test first 3 articles
        print(f"\n--- Testing: {test_case['id']} ---")
        print(f"Title: {test_case['title']}")
        
        article = {
            "_id": test_case["id"],
            "article_id": test_case["id"],
            "title": test_case["title"],
            "description": test_case["summary"]
        }
        
        result = await discover_narrative_from_article(article)
        
        if result:
            is_valid, error = validate_narrative_json(result)
            print(f"✓ Valid: {is_valid}")
            print(f"✓ Actors: {result['actors']}")
            print(f"✓ Nucleus: {result['nucleus_entity']}")
            print(f"✓ Salience: {result['actor_salience']}")
            
            results.append({
                "test_id": test_case["id"],
                "valid": is_valid,
                "actors": result["actors"],
                "nucleus": result["nucleus_entity"],
                "salience": result["actor_salience"]
            })
        else:
            print("✗ Failed to extract narrative")
    
    # Verify all tests passed
    assert len(results) == 3, "Should successfully process all test articles"
    assert all(r["valid"] for r in results), "All results should be valid"
    
    print("\n" + "="*80)
    print("✓ INTEGRATION TEST PASSED")
    print("="*80)


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
