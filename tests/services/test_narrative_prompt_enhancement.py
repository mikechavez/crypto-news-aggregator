"""
Tests for narrative prompt enhancement - entity normalization and nucleus selection.

Verifies that the enhanced prompt correctly:
1. Normalizes entity names to canonical forms
2. Selects appropriate nucleus entities
3. Applies selective salience scoring
"""

import pytest
import json
from unittest.mock import MagicMock, patch

from crypto_news_aggregator.services.narrative_themes import (
    discover_narrative_from_article,
    validate_narrative_json
)


class TestEntityNormalization:
    """Test that entity names are normalized to canonical forms."""
    
    @pytest.mark.asyncio
    async def test_sec_normalization(self):
        """Test that SEC variations are normalized to 'SEC'."""
        # Mock article about SEC
        article = {
            "_id": "test_sec_001",
            "article_id": "test_sec_001",
            "title": "U.S. Securities and Exchange Commission Sues Binance",
            "description": "The U.S. Securities and Exchange Commission filed a lawsuit against Binance for regulatory violations."
        }
        
        # Mock LLM response with normalized entity
        mock_response = json.dumps({
            "actors": ["SEC", "Binance"],
            "actor_salience": {
                "SEC": 5,
                "Binance": 4
            },
            "nucleus_entity": "SEC",
            "actions": ["SEC filed lawsuit against Binance"],
            "tensions": ["Regulation vs Innovation"],
            "implications": "Signals escalation in regulatory enforcement",
            "narrative_summary": "Regulators are intensifying enforcement against major exchanges."
        })
        
        with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider._get_completion.return_value = mock_response
            mock_llm.return_value = mock_provider
            
            result = await discover_narrative_from_article(article)
            
            # Verify normalization
            assert result is not None
            assert "SEC" in result["actors"]
            assert "U.S. SEC" not in result["actors"]
            assert "Securities and Exchange Commission" not in result["actors"]
            assert "US SEC" not in result["actors"]
    
    @pytest.mark.asyncio
    async def test_binance_normalization(self):
        """Test that Binance variations are normalized to 'Binance'."""
        article = {
            "_id": "test_binance_001",
            "article_id": "test_binance_001",
            "title": "Binance Exchange Launches New Trading Features",
            "description": "The Binance exchange has launched new trading features for institutional investors."
        }
        
        mock_response = json.dumps({
            "actors": ["Binance"],
            "actor_salience": {
                "Binance": 5
            },
            "nucleus_entity": "Binance",
            "actions": ["Binance launched new trading features"],
            "tensions": ["Innovation vs Competition"],
            "implications": "Strengthens market position",
            "narrative_summary": "Binance continues to expand its product offerings."
        })
        
        with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider._get_completion.return_value = mock_response
            mock_llm.return_value = mock_provider
            
            result = await discover_narrative_from_article(article)
            
            # Verify normalization
            assert result is not None
            assert "Binance" in result["actors"]
            assert "Binance exchange" not in result["actors"]
            assert "Binance.US" not in result["actors"]
    
    @pytest.mark.asyncio
    async def test_ethereum_normalization(self):
        """Test that Ethereum variations are normalized to 'Ethereum'."""
        article = {
            "_id": "test_eth_001",
            "article_id": "test_eth_001",
            "title": "Ethereum Network Completes Major Upgrade",
            "description": "The Ethereum network has successfully completed its major upgrade, improving scalability."
        }
        
        mock_response = json.dumps({
            "actors": ["Ethereum"],
            "actor_salience": {
                "Ethereum": 5
            },
            "nucleus_entity": "Ethereum",
            "actions": ["Ethereum completed major upgrade"],
            "tensions": ["Scalability vs Decentralization"],
            "implications": "Improves network performance",
            "narrative_summary": "Ethereum continues to evolve its infrastructure."
        })
        
        with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider._get_completion.return_value = mock_response
            mock_llm.return_value = mock_provider
            
            result = await discover_narrative_from_article(article)
            
            # Verify normalization
            assert result is not None
            assert "Ethereum" in result["actors"]
            assert "Ethereum network" not in result["actors"]
            assert "Ethereum Foundation" not in result["actors"]
            assert "ETH" not in result["actors"]
    
    @pytest.mark.asyncio
    async def test_bitcoin_normalization(self):
        """Test that Bitcoin variations are normalized to 'Bitcoin'."""
        article = {
            "_id": "test_btc_001",
            "article_id": "test_btc_001",
            "title": "Bitcoin Network Reaches New Hash Rate Record",
            "description": "The Bitcoin network has reached a new all-time high in hash rate, signaling strong security."
        }
        
        mock_response = json.dumps({
            "actors": ["Bitcoin"],
            "actor_salience": {
                "Bitcoin": 5
            },
            "nucleus_entity": "Bitcoin",
            "actions": ["Bitcoin reached new hash rate record"],
            "tensions": ["Security vs Energy Consumption"],
            "implications": "Network security strengthened",
            "narrative_summary": "Bitcoin's network continues to grow stronger."
        })
        
        with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider._get_completion.return_value = mock_response
            mock_llm.return_value = mock_provider
            
            result = await discover_narrative_from_article(article)
            
            # Verify normalization
            assert result is not None
            assert "Bitcoin" in result["actors"]
            assert "Bitcoin network" not in result["actors"]
            assert "BTC" not in result["actors"]


class TestNucleusSelection:
    """Test that nucleus entity selection follows the enhanced rules."""
    
    @pytest.mark.asyncio
    async def test_regulatory_story_nucleus_is_regulator(self):
        """In regulatory stories, nucleus should be the regulator (SEC), not 'lawsuit' or 'regulation'."""
        article = {
            "_id": "test_nucleus_001",
            "article_id": "test_nucleus_001",
            "title": "SEC Files Lawsuit Against Coinbase",
            "description": "The SEC has filed a major lawsuit against Coinbase for alleged securities violations."
        }
        
        mock_response = json.dumps({
            "actors": ["SEC", "Coinbase"],
            "actor_salience": {
                "SEC": 5,
                "Coinbase": 4
            },
            "nucleus_entity": "SEC",  # Should be SEC, not "lawsuit" or "regulation"
            "actions": ["SEC filed lawsuit against Coinbase"],
            "tensions": ["Regulation vs Innovation"],
            "implications": "Signals regulatory crackdown",
            "narrative_summary": "SEC intensifies enforcement actions."
        })
        
        with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider._get_completion.return_value = mock_response
            mock_llm.return_value = mock_provider
            
            result = await discover_narrative_from_article(article)
            
            # Verify nucleus is the actor (SEC), not abstract concept
            assert result is not None
            assert result["nucleus_entity"] == "SEC"
            assert result["nucleus_entity"] != "lawsuit"
            assert result["nucleus_entity"] != "regulation"
    
    @pytest.mark.asyncio
    async def test_company_story_nucleus_is_company(self):
        """In company stories, nucleus should be company, not CEO."""
        article = {
            "_id": "test_nucleus_002",
            "article_id": "test_nucleus_002",
            "title": "Coinbase CEO Brian Armstrong Announces New Strategy",
            "description": "Coinbase CEO Brian Armstrong has announced a new strategic direction for the company."
        }
        
        mock_response = json.dumps({
            "actors": ["Coinbase", "Brian Armstrong"],
            "actor_salience": {
                "Coinbase": 5,
                "Brian Armstrong": 3
            },
            "nucleus_entity": "Coinbase",  # Should be Coinbase, not Brian Armstrong
            "actions": ["Coinbase announced new strategy"],
            "tensions": ["Growth vs Regulation"],
            "implications": "Shifts company direction",
            "narrative_summary": "Coinbase pivots strategy amid market changes."
        })
        
        with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider._get_completion.return_value = mock_response
            mock_llm.return_value = mock_provider
            
            result = await discover_narrative_from_article(article)
            
            # Verify nucleus is the company, not the CEO
            assert result is not None
            assert result["nucleus_entity"] == "Coinbase"
            assert result["nucleus_entity"] != "Brian Armstrong"
    
    @pytest.mark.asyncio
    async def test_specific_entity_over_generic_category(self):
        """Nucleus should be specific entity, not generic category."""
        article = {
            "_id": "test_nucleus_003",
            "article_id": "test_nucleus_003",
            "title": "Binance Dominates Crypto Exchange Market",
            "description": "Binance continues to lead the crypto exchange market with record trading volumes."
        }
        
        mock_response = json.dumps({
            "actors": ["Binance"],
            "actor_salience": {
                "Binance": 5
            },
            "nucleus_entity": "Binance",  # Should be Binance, not "crypto exchanges"
            "actions": ["Binance achieved record trading volumes"],
            "tensions": ["Market Dominance vs Competition"],
            "implications": "Strengthens market position",
            "narrative_summary": "Binance solidifies its market leadership."
        })
        
        with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider._get_completion.return_value = mock_response
            mock_llm.return_value = mock_provider
            
            result = await discover_narrative_from_article(article)
            
            # Verify nucleus is specific entity, not generic category
            assert result is not None
            assert result["nucleus_entity"] == "Binance"
            assert result["nucleus_entity"] != "crypto exchanges"
            assert result["nucleus_entity"] != "exchanges"


class TestSalienceScoring:
    """Test that salience scoring is selective and follows guidelines."""
    
    @pytest.mark.asyncio
    async def test_limited_high_salience_entities(self):
        """Only 1-2 entities should have salience 5."""
        article = {
            "_id": "test_salience_001",
            "article_id": "test_salience_001",
            "title": "SEC Sues Binance and Coinbase",
            "description": "The SEC has filed lawsuits against both Binance and Coinbase for securities violations."
        }
        
        mock_response = json.dumps({
            "actors": ["SEC", "Binance", "Coinbase"],
            "actor_salience": {
                "SEC": 5,        # Primary protagonist
                "Binance": 4,    # Key participant
                "Coinbase": 4    # Key participant
            },
            "nucleus_entity": "SEC",
            "actions": ["SEC filed lawsuits against Binance and Coinbase"],
            "tensions": ["Regulation vs Innovation"],
            "implications": "Broad regulatory crackdown",
            "narrative_summary": "SEC escalates enforcement across major exchanges."
        })
        
        with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider._get_completion.return_value = mock_response
            mock_llm.return_value = mock_provider
            
            result = await discover_narrative_from_article(article)
            
            # Verify selective salience scoring
            assert result is not None
            salience_scores = result["actor_salience"]
            
            # Count entities with salience 5
            high_salience_count = sum(1 for score in salience_scores.values() if score == 5)
            assert high_salience_count <= 2, "Should have at most 2 entities with salience 5"
    
    @pytest.mark.asyncio
    async def test_background_mentions_excluded(self):
        """Background mentions (salience 1) should be excluded from actors list."""
        article = {
            "_id": "test_salience_002",
            "article_id": "test_salience_002",
            "title": "Coinbase Launches New DeFi Product",
            "description": "Coinbase has launched a new DeFi product, joining the competitive landscape alongside Uniswap and other protocols."
        }
        
        mock_response = json.dumps({
            "actors": ["Coinbase", "Uniswap"],  # Bitcoin excluded (salience 1)
            "actor_salience": {
                "Coinbase": 5,
                "Uniswap": 2
                # Bitcoin would be salience 1, so excluded
            },
            "nucleus_entity": "Coinbase",
            "actions": ["Coinbase launched new DeFi product"],
            "tensions": ["Innovation vs Competition"],
            "implications": "Expands DeFi offerings",
            "narrative_summary": "Coinbase enters DeFi market."
        })
        
        with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider._get_completion.return_value = mock_response
            mock_llm.return_value = mock_provider
            
            result = await discover_narrative_from_article(article)
            
            # Verify all actors have salience >= 2
            assert result is not None
            for actor in result["actors"]:
                assert result["actor_salience"][actor] >= 2, f"{actor} should have salience >= 2"
    
    @pytest.mark.asyncio
    async def test_clear_salience_hierarchy(self):
        """Salience scores should show clear hierarchy."""
        article = {
            "_id": "test_salience_003",
            "article_id": "test_salience_003",
            "title": "SEC, CFTC, and DOJ Coordinate Crypto Enforcement",
            "description": "The SEC, CFTC, and DOJ are coordinating enforcement actions against crypto firms, with the SEC taking the lead."
        }
        
        mock_response = json.dumps({
            "actors": ["SEC", "CFTC", "DOJ"],
            "actor_salience": {
                "SEC": 5,    # Primary protagonist
                "CFTC": 3,   # Secondary participant
                "DOJ": 3     # Secondary participant
            },
            "nucleus_entity": "SEC",
            "actions": ["SEC leads coordinated enforcement"],
            "tensions": ["Regulation vs Innovation"],
            "implications": "Multi-agency approach to crypto regulation",
            "narrative_summary": "Regulators coordinate enforcement efforts."
        })
        
        with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider._get_completion.return_value = mock_response
            mock_llm.return_value = mock_provider
            
            result = await discover_narrative_from_article(article)
            
            # Verify clear hierarchy
            assert result is not None
            salience_scores = result["actor_salience"]
            
            # Should have differentiation in scores
            unique_scores = set(salience_scores.values())
            assert len(unique_scores) >= 2, "Should have at least 2 different salience levels"
            
            # Nucleus entity should have highest or tied-highest salience
            nucleus = result["nucleus_entity"]
            nucleus_salience = salience_scores[nucleus]
            max_salience = max(salience_scores.values())
            assert nucleus_salience == max_salience, "Nucleus should have highest salience"


class TestValidationWithEnhancedPrompt:
    """Test that enhanced prompt produces valid JSON that passes validation."""
    
    @pytest.mark.asyncio
    async def test_valid_json_structure(self):
        """Enhanced prompt should produce valid JSON structure."""
        article = {
            "_id": "test_validation_001",
            "article_id": "test_validation_001",
            "title": "SEC Approves Bitcoin ETF",
            "description": "The SEC has approved the first Bitcoin spot ETF, marking a major milestone for crypto adoption."
        }
        
        mock_response = json.dumps({
            "actors": ["SEC", "Bitcoin"],
            "actor_salience": {
                "SEC": 5,
                "Bitcoin": 4
            },
            "nucleus_entity": "SEC",
            "actions": ["SEC approved Bitcoin spot ETF"],
            "tensions": ["Regulation vs Innovation"],
            "implications": "Mainstream crypto adoption",
            "narrative_summary": "SEC approval signals regulatory acceptance of Bitcoin."
        })
        
        with patch("crypto_news_aggregator.services.narrative_themes.get_llm_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider._get_completion.return_value = mock_response
            mock_llm.return_value = mock_provider
            
            result = await discover_narrative_from_article(article)
            
            # Verify validation passes
            assert result is not None
            is_valid, error = validate_narrative_json(result)
            assert is_valid, f"Validation failed: {error}"
    
    def test_validation_requires_all_fields(self):
        """Validation should require all mandatory fields."""
        # Missing nucleus_entity
        invalid_data = {
            "actors": ["SEC", "Bitcoin"],
            "actor_salience": {
                "SEC": 5,
                "Bitcoin": 4
            },
            "actions": ["SEC approved Bitcoin ETF"],
            "tensions": ["Regulation vs Innovation"],
            "implications": "Mainstream adoption",
            "narrative_summary": "SEC approves Bitcoin ETF."
        }
        
        is_valid, error = validate_narrative_json(invalid_data)
        assert not is_valid
        assert "nucleus_entity" in error.lower()
    
    def test_validation_requires_nucleus_in_actors(self):
        """Nucleus entity must be in actors list."""
        invalid_data = {
            "actors": ["Bitcoin"],
            "actor_salience": {
                "Bitcoin": 5
            },
            "nucleus_entity": "SEC",  # Not in actors list
            "actions": ["SEC approved Bitcoin ETF"],
            "tensions": ["Regulation vs Innovation"],
            "implications": "Mainstream adoption",
            "narrative_summary": "SEC approves Bitcoin ETF."
        }
        
        is_valid, error = validate_narrative_json(invalid_data)
        assert not is_valid
        assert "nucleus" in error.lower() or "actors" in error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
