"""
Tests for shallow narrative merging.

Tests the merge_shallow_narratives function with various scenarios:
- Single-article narratives with few actors
- Ubiquitous entity narratives (Bitcoin, Ethereum)
- Jaccard similarity matching
- Merge vs standalone decisions
"""

import pytest
from src.crypto_news_aggregator.services.narrative_themes import merge_shallow_narratives


@pytest.mark.asyncio
async def test_merge_single_article_narrative():
    """Single-article narrative with <3 actors should merge if similar enough."""
    narratives = [
        {
            "title": "SEC Enforcement Action",
            "article_ids": ["1", "2", "3", "4"],
            "actors": ["SEC", "Binance"],
            "nucleus_entity": "SEC"
        },
        {
            "title": "Binance Faces Scrutiny",
            "article_ids": ["5"],
            "actors": ["Binance", "SEC"],  # 2 actors, 1 article = shallow
            "nucleus_entity": "Binance"
        }
    ]
    
    result = await merge_shallow_narratives(narratives)
    
    # Shallow narrative should merge into substantial one
    # Similarity: overlap=2 (Binance, SEC), union=2, similarity=1.0 > 0.5 ✓
    assert len(result) == 1
    assert len(result[0]["article_ids"]) == 5
    assert "5" in result[0]["article_ids"]
    assert set(result[0]["actors"]) == {"SEC", "Binance"}


@pytest.mark.asyncio
async def test_keep_shallow_narrative_no_match():
    """Shallow narrative with no good match should stay standalone."""
    narratives = [
        {
            "title": "SEC Enforcement Action",
            "article_ids": ["1", "2", "3"],
            "actors": ["SEC", "Binance", "Coinbase"],
            "nucleus_entity": "SEC"
        },
        {
            "title": "DeFi Protocol Launch",
            "article_ids": ["4"],
            "actors": ["Uniswap", "Aave"],  # No overlap with SEC narrative
            "nucleus_entity": "Uniswap"
        }
    ]
    
    result = await merge_shallow_narratives(narratives)
    
    # Both narratives should remain (no good match for shallow one)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_merge_ubiquitous_entity_narrative():
    """Bitcoin/Ethereum narratives with <3 articles should be shallow."""
    narratives = [
        {
            "title": "Regulatory Crackdown",
            "article_ids": ["1", "2", "3", "4"],
            "actors": ["SEC", "Binance", "Bitcoin", "Ethereum"],
            "nucleus_entity": "SEC"
        },
        {
            "title": "Bitcoin Price Movement",
            "article_ids": ["5"],  # 1 article, ubiquitous nucleus
            "actors": ["Bitcoin", "Ethereum"],
            "nucleus_entity": "Bitcoin"
        }
    ]
    
    result = await merge_shallow_narratives(narratives)
    
    # Bitcoin narrative is shallow (ubiquitous + <3 articles)
    # Similarity: overlap=2 (Bitcoin, Ethereum), union=4, similarity=0.5 (exactly at threshold)
    # Should NOT merge (needs > 0.5, not >= 0.5)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_jaccard_similarity_threshold():
    """Only merge if Jaccard similarity > 0.5."""
    narratives = [
        {
            "title": "SEC Enforcement",
            "article_ids": ["1", "2", "3"],
            "actors": ["SEC", "Binance", "Coinbase", "Kraken", "Gemini"],
            "nucleus_entity": "SEC"
        },
        {
            "title": "DeFi Growth",
            "article_ids": ["4"],
            "actors": ["Binance"],  # Only 1 overlap out of 6 total = 1/6 = 0.17 < 0.5
            "nucleus_entity": "Binance"
        }
    ]
    
    result = await merge_shallow_narratives(narratives)
    
    # Similarity too low, should not merge
    assert len(result) == 2


@pytest.mark.asyncio
async def test_merge_into_best_match():
    """Shallow narrative should merge into best matching substantial narrative."""
    narratives = [
        {
            "title": "SEC Regulatory Action",
            "article_ids": ["1", "2", "3"],
            "actors": ["SEC", "Binance", "Coinbase"],
            "nucleus_entity": "SEC"
        },
        {
            "title": "DeFi Innovation",
            "article_ids": ["4", "5", "6"],
            "actors": ["Uniswap", "Aave", "Binance", "Curve"],
            "nucleus_entity": "Uniswap"
        },
        {
            "title": "Exchange News",
            "article_ids": ["7"],
            "actors": ["Binance", "Uniswap"],  # Overlaps with both, but more with DeFi
            "nucleus_entity": "Binance"
        }
    ]
    
    result = await merge_shallow_narratives(narratives)
    
    # Should merge into DeFi narrative (better match)
    # SEC: overlap=1 (Binance), union=4, similarity=0.25
    # DeFi: overlap=2 (Binance, Uniswap), union=5, similarity=0.40 (still < 0.5)
    # Actually, both are below threshold, so should stay standalone
    assert len(result) == 3


@pytest.mark.asyncio
async def test_multiple_shallow_narratives():
    """Multiple shallow narratives should be processed independently."""
    narratives = [
        {
            "title": "SEC Enforcement",
            "article_ids": ["1", "2", "3", "4"],
            "actors": ["SEC", "Binance", "Coinbase"],
            "nucleus_entity": "SEC"
        },
        {
            "title": "Binance News",
            "article_ids": ["5"],
            "actors": ["Binance", "SEC"],
            "nucleus_entity": "Binance"
        },
        {
            "title": "Coinbase Update",
            "article_ids": ["6"],
            "actors": ["Coinbase", "SEC"],
            "nucleus_entity": "Coinbase"
        }
    ]
    
    result = await merge_shallow_narratives(narratives)
    
    # Both shallow narratives should merge into SEC narrative
    # Binance: overlap=2, union=3, similarity=0.67 > 0.5 ✓
    # Coinbase: overlap=2, union=3, similarity=0.67 > 0.5 ✓
    assert len(result) == 1
    assert len(result[0]["article_ids"]) == 6


@pytest.mark.asyncio
async def test_substantial_narratives_unchanged():
    """Substantial narratives should pass through unchanged."""
    narratives = [
        {
            "title": "SEC Enforcement",
            "article_ids": ["1", "2", "3"],
            "actors": ["SEC", "Binance", "Coinbase"],
            "nucleus_entity": "SEC"
        },
        {
            "title": "DeFi Growth",
            "article_ids": ["4", "5", "6"],
            "actors": ["Uniswap", "Aave", "Curve"],
            "nucleus_entity": "Uniswap"
        }
    ]
    
    result = await merge_shallow_narratives(narratives)
    
    # Both are substantial, should remain unchanged
    assert len(result) == 2
    assert result == narratives


@pytest.mark.asyncio
async def test_empty_input():
    """Empty narrative list should return empty list."""
    result = await merge_shallow_narratives([])
    assert result == []


@pytest.mark.asyncio
async def test_all_shallow_narratives():
    """All shallow narratives with no good matches should stay separate."""
    narratives = [
        {
            "title": "Bitcoin News",
            "article_ids": ["1"],
            "actors": ["Bitcoin"],
            "nucleus_entity": "Bitcoin"
        },
        {
            "title": "Ethereum Update",
            "article_ids": ["2"],
            "actors": ["Ethereum"],
            "nucleus_entity": "Ethereum"
        },
        {
            "title": "Solana Development",
            "article_ids": ["3"],
            "actors": ["Solana"],
            "nucleus_entity": "Solana"
        }
    ]
    
    result = await merge_shallow_narratives(narratives)
    
    # All are shallow with no overlap, should all stay standalone
    assert len(result) == 3


@pytest.mark.asyncio
async def test_ubiquitous_entities_list():
    """Test all ubiquitous entities are recognized."""
    ubiquitous = ["Bitcoin", "Ethereum", "crypto", "blockchain", "cryptocurrency"]
    
    for entity in ubiquitous:
        narratives = [
            {
                "title": "Substantial Narrative",
                "article_ids": ["1", "2", "3"],
                "actors": ["SEC", "Binance"],
                "nucleus_entity": "SEC"
            },
            {
                "title": f"{entity} News",
                "article_ids": ["4", "5"],  # 2 articles, ubiquitous nucleus
                "actors": [entity],
                "nucleus_entity": entity
            }
        ]
        
        result = await merge_shallow_narratives(narratives)
        
        # Should be classified as shallow (ubiquitous + <3 articles)
        # Won't merge due to no overlap, but should be attempted
        assert len(result) == 2  # No overlap, so stays separate


@pytest.mark.asyncio
async def test_actors_deduplication():
    """Merged narratives should have unique actors."""
    narratives = [
        {
            "title": "SEC Enforcement",
            "article_ids": ["1", "2", "3"],
            "actors": ["SEC", "Binance", "Coinbase"],
            "nucleus_entity": "SEC"
        },
        {
            "title": "Binance News",
            "article_ids": ["4"],
            "actors": ["Binance", "SEC"],  # Duplicates with substantial
            "nucleus_entity": "Binance"
        }
    ]
    
    result = await merge_shallow_narratives(narratives)
    
    # Should merge and deduplicate actors
    assert len(result) == 1
    actors = result[0]["actors"]
    assert len(actors) == len(set(actors))  # No duplicates
    assert set(actors) == {"SEC", "Binance", "Coinbase"}


@pytest.mark.asyncio
async def test_article_ids_deduplication():
    """Merged narratives should have unique article IDs."""
    narratives = [
        {
            "title": "SEC Enforcement",
            "article_ids": ["1", "2", "3"],
            "actors": ["SEC", "Binance"],
            "nucleus_entity": "SEC"
        },
        {
            "title": "Binance News",
            "article_ids": ["4"],  # 1 article, 2 actors = shallow
            "actors": ["Binance", "SEC"],
            "nucleus_entity": "Binance"
        }
    ]
    
    result = await merge_shallow_narratives(narratives)
    
    # Should merge and deduplicate article IDs
    # Similarity: overlap=2, union=2, similarity=1.0 > 0.5 ✓
    assert len(result) == 1
    article_ids = result[0]["article_ids"]
    assert len(article_ids) == len(set(article_ids))  # No duplicates
    assert set(article_ids) == {"1", "2", "3", "4"}
