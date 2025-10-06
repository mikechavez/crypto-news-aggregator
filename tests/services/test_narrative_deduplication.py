"""
Tests for narrative deduplication service.
"""

import pytest
from crypto_news_aggregator.services.narrative_deduplication import (
    calculate_similarity,
    merge_similar_narratives,
    deduplicate_narratives,
    _merge_narrative_group
)


class TestCalculateSimilarity:
    """Tests for Jaccard similarity calculation."""
    
    def test_identical_narratives(self):
        """Test that identical entity sets return 1.0 similarity."""
        narrative_a = {"entities": ["Bitcoin", "Ethereum", "Solana"]}
        narrative_b = {"entities": ["Bitcoin", "Ethereum", "Solana"]}
        
        similarity = calculate_similarity(narrative_a, narrative_b)
        assert similarity == 1.0
    
    def test_no_overlap(self):
        """Test that completely different entity sets return 0.0 similarity."""
        narrative_a = {"entities": ["Bitcoin", "Ethereum"]}
        narrative_b = {"entities": ["Cardano", "Polkadot"]}
        
        similarity = calculate_similarity(narrative_a, narrative_b)
        assert similarity == 0.0
    
    def test_partial_overlap(self):
        """Test Jaccard similarity with partial overlap."""
        # Entities: {Bitcoin, Ethereum} vs {Bitcoin, Solana}
        # Intersection: {Bitcoin} = 1 element
        # Union: {Bitcoin, Ethereum, Solana} = 3 elements
        # Jaccard = 1/3 ≈ 0.333
        narrative_a = {"entities": ["Bitcoin", "Ethereum"]}
        narrative_b = {"entities": ["Bitcoin", "Solana"]}
        
        similarity = calculate_similarity(narrative_a, narrative_b)
        assert abs(similarity - 0.333) < 0.01
    
    def test_high_overlap(self):
        """Test high similarity (above typical threshold)."""
        # Entities: {Bitcoin, Ethereum, Solana} vs {Bitcoin, Ethereum, Cardano}
        # Intersection: {Bitcoin, Ethereum} = 2 elements
        # Union: {Bitcoin, Ethereum, Solana, Cardano} = 4 elements
        # Jaccard = 2/4 = 0.5
        narrative_a = {"entities": ["Bitcoin", "Ethereum", "Solana"]}
        narrative_b = {"entities": ["Bitcoin", "Ethereum", "Cardano"]}
        
        similarity = calculate_similarity(narrative_a, narrative_b)
        assert similarity == 0.5
    
    def test_empty_entities(self):
        """Test that empty entity lists return 0.0 similarity."""
        narrative_a = {"entities": []}
        narrative_b = {"entities": ["Bitcoin"]}
        
        similarity = calculate_similarity(narrative_a, narrative_b)
        assert similarity == 0.0
    
    def test_missing_entities_key(self):
        """Test handling of missing 'entities' key."""
        narrative_a = {}
        narrative_b = {"entities": ["Bitcoin"]}
        
        similarity = calculate_similarity(narrative_a, narrative_b)
        assert similarity == 0.0


class TestMergeSimilarNarratives:
    """Tests for narrative merging logic."""
    
    def test_no_duplicates(self):
        """Test that distinct narratives are not merged."""
        narratives = [
            {
                "theme": "Bitcoin Rally",
                "entities": ["Bitcoin"],
                "story": "Bitcoin surges",
                "article_count": 5
            },
            {
                "theme": "Ethereum Update",
                "entities": ["Ethereum"],
                "story": "Ethereum upgrades",
                "article_count": 3
            }
        ]
        
        result = merge_similar_narratives(narratives, threshold=0.7)
        assert len(result) == 2
    
    def test_merge_identical_narratives(self):
        """Test merging narratives with identical entity sets."""
        narratives = [
            {
                "theme": "Bitcoin & Ethereum Rally",
                "entities": ["Bitcoin", "Ethereum"],
                "story": "Crypto markets surge",
                "article_count": 5
            },
            {
                "theme": "BTC/ETH Pump",
                "entities": ["Bitcoin", "Ethereum"],
                "story": "Major cryptos rally",
                "article_count": 3
            }
        ]
        
        result = merge_similar_narratives(narratives, threshold=0.7)
        
        # Should merge into 1 narrative
        assert len(result) == 1
        
        # Should keep the narrative with more articles
        assert result[0]["theme"] == "Bitcoin & Ethereum Rally"
        
        # Should sum article counts
        assert result[0]["article_count"] == 8
        
        # Should preserve entities
        assert set(result[0]["entities"]) == {"Bitcoin", "Ethereum"}
    
    def test_merge_high_similarity(self):
        """Test merging narratives with high Jaccard similarity (>0.7)."""
        # Similarity calculation:
        # Intersection: {Bitcoin, Ethereum, Solana} = 3 elements
        # Union: {Bitcoin, Ethereum, Solana, BNB} = 4 elements
        # Jaccard = 3/4 = 0.75 (above threshold)
        narratives = [
            {
                "theme": "Major Crypto Rally",
                "entities": ["Bitcoin", "Ethereum", "Solana", "BNB"],
                "story": "Top cryptos surge",
                "article_count": 10
            },
            {
                "theme": "BTC/ETH/SOL Pump",
                "entities": ["Bitcoin", "Ethereum", "Solana"],
                "story": "Leading coins rally",
                "article_count": 7
            }
        ]
        
        result = merge_similar_narratives(narratives, threshold=0.7)
        
        # Should merge into 1 narrative
        assert len(result) == 1
        
        # Should keep narrative with more articles
        assert result[0]["theme"] == "Major Crypto Rally"
        
        # Should merge all unique entities
        assert set(result[0]["entities"]) == {"Bitcoin", "Ethereum", "Solana", "BNB"}
        
        # Should sum article counts
        assert result[0]["article_count"] == 17
    
    def test_no_merge_below_threshold(self):
        """Test that narratives below threshold are not merged."""
        # Similarity = 1/4 = 0.25 (below threshold of 0.7)
        narratives = [
            {
                "theme": "Bitcoin Rally",
                "entities": ["Bitcoin", "Ethereum"],
                "story": "BTC/ETH surge",
                "article_count": 5
            },
            {
                "theme": "Altcoin Season",
                "entities": ["Bitcoin", "Cardano"],
                "story": "Alts pumping",
                "article_count": 3
            }
        ]
        
        result = merge_similar_narratives(narratives, threshold=0.7)
        
        # Should not merge (similarity too low)
        assert len(result) == 2
    
    def test_empty_input(self):
        """Test handling of empty narrative list."""
        result = merge_similar_narratives([], threshold=0.7)
        assert result == []
    
    def test_single_narrative(self):
        """Test handling of single narrative."""
        narratives = [
            {
                "theme": "Bitcoin Rally",
                "entities": ["Bitcoin"],
                "story": "BTC surges",
                "article_count": 5
            }
        ]
        
        result = merge_similar_narratives(narratives, threshold=0.7)
        assert len(result) == 1
        assert result[0] == narratives[0]
    
    def test_multiple_merge_groups(self):
        """Test merging with multiple distinct groups."""
        narratives = [
            # Group 1: Bitcoin/Ethereum (identical)
            {
                "theme": "BTC/ETH Rally",
                "entities": ["Bitcoin", "Ethereum"],
                "story": "Major coins surge",
                "article_count": 10
            },
            {
                "theme": "Bitcoin & Ethereum Pump",
                "entities": ["Bitcoin", "Ethereum"],
                "story": "Top 2 rally",
                "article_count": 5
            },
            # Group 2: Solana/Cardano (identical)
            {
                "theme": "Altcoin Rally",
                "entities": ["Solana", "Cardano"],
                "story": "Alts pumping",
                "article_count": 8
            },
            {
                "theme": "SOL/ADA Surge",
                "entities": ["Solana", "Cardano"],
                "story": "Smart contract platforms rally",
                "article_count": 6
            }
        ]
        
        result = merge_similar_narratives(narratives, threshold=0.7)
        
        # Should have 2 merged groups
        assert len(result) == 2
        
        # Check that each group was merged correctly
        themes = {n["theme"] for n in result}
        assert "BTC/ETH Rally" in themes
        assert "Altcoin Rally" in themes


class TestMergeNarrativeGroup:
    """Tests for internal merge group function."""
    
    def test_merge_keeps_strongest_narrative(self):
        """Test that merge keeps the narrative with most articles as base."""
        narratives = [
            {
                "theme": "Weak Narrative",
                "entities": ["Bitcoin"],
                "story": "Weak story",
                "article_count": 2
            },
            {
                "theme": "Strong Narrative",
                "entities": ["Bitcoin", "Ethereum"],
                "story": "Strong story",
                "article_count": 10
            },
            {
                "theme": "Medium Narrative",
                "entities": ["Bitcoin"],
                "story": "Medium story",
                "article_count": 5
            }
        ]
        
        result = _merge_narrative_group(narratives)
        
        # Should use the strongest narrative as base
        assert result["theme"] == "Strong Narrative"
        assert result["story"] == "Strong story"
    
    def test_merge_combines_entities(self):
        """Test that merge combines all unique entities."""
        narratives = [
            {
                "theme": "Narrative 1",
                "entities": ["Bitcoin", "Ethereum"],
                "story": "Story 1",
                "article_count": 5
            },
            {
                "theme": "Narrative 2",
                "entities": ["Bitcoin", "Solana"],
                "story": "Story 2",
                "article_count": 3
            }
        ]
        
        result = _merge_narrative_group(narratives)
        
        # Should have all unique entities
        assert set(result["entities"]) == {"Bitcoin", "Ethereum", "Solana"}
    
    def test_merge_sums_article_counts(self):
        """Test that merge sums article counts."""
        narratives = [
            {"theme": "N1", "entities": ["Bitcoin"], "story": "S1", "article_count": 5},
            {"theme": "N2", "entities": ["Bitcoin"], "story": "S2", "article_count": 3},
            {"theme": "N3", "entities": ["Bitcoin"], "story": "S3", "article_count": 7}
        ]
        
        result = _merge_narrative_group(narratives)
        
        # Should sum all article counts
        assert result["article_count"] == 15


class TestDeduplicateNarratives:
    """Tests for main deduplication entry point."""
    
    def test_deduplicate_returns_count(self):
        """Test that deduplicate returns both narratives and merge count."""
        narratives = [
            {
                "theme": "Bitcoin Rally",
                "entities": ["Bitcoin", "Ethereum"],
                "story": "Crypto surge",
                "article_count": 10
            },
            {
                "theme": "BTC/ETH Pump",
                "entities": ["Bitcoin", "Ethereum"],
                "story": "Major coins rally",
                "article_count": 5
            }
        ]
        
        deduplicated, num_merged = deduplicate_narratives(narratives, threshold=0.7)
        
        assert len(deduplicated) == 1
        assert num_merged == 1
    
    def test_deduplicate_empty_list(self):
        """Test deduplication of empty list."""
        deduplicated, num_merged = deduplicate_narratives([], threshold=0.7)
        
        assert deduplicated == []
        assert num_merged == 0
    
    def test_deduplicate_no_merges(self):
        """Test deduplication when no merges occur."""
        narratives = [
            {
                "theme": "Bitcoin Rally",
                "entities": ["Bitcoin"],
                "story": "BTC surges",
                "article_count": 5
            },
            {
                "theme": "Ethereum Update",
                "entities": ["Ethereum"],
                "story": "ETH upgrades",
                "article_count": 3
            }
        ]
        
        deduplicated, num_merged = deduplicate_narratives(narratives, threshold=0.7)
        
        assert len(deduplicated) == 2
        assert num_merged == 0
    
    def test_custom_threshold(self):
        """Test deduplication with custom threshold."""
        # Similarity = 1/3 ≈ 0.333
        narratives = [
            {
                "theme": "Bitcoin Rally",
                "entities": ["Bitcoin", "Ethereum"],
                "story": "BTC/ETH surge",
                "article_count": 5
            },
            {
                "theme": "Bitcoin News",
                "entities": ["Bitcoin", "Cardano"],
                "story": "BTC updates",
                "article_count": 3
            }
        ]
        
        # Should not merge with high threshold
        deduplicated_high, num_merged_high = deduplicate_narratives(narratives, threshold=0.7)
        assert len(deduplicated_high) == 2
        assert num_merged_high == 0
        
        # Should merge with low threshold
        deduplicated_low, num_merged_low = deduplicate_narratives(narratives, threshold=0.3)
        assert len(deduplicated_low) == 1
        assert num_merged_low == 1
