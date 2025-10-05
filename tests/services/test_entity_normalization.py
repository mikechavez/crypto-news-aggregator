"""
Tests for entity normalization service.
"""

import pytest
from crypto_news_aggregator.services.entity_normalization import (
    normalize_entity_name,
    get_canonical_names,
    get_variants,
    is_canonical,
)


class TestNormalizeEntityName:
    """Tests for normalize_entity_name function."""
    
    def test_normalize_btc_variants(self):
        """Test that all BTC variants normalize to Bitcoin."""
        assert normalize_entity_name("BTC") == "Bitcoin"
        assert normalize_entity_name("$BTC") == "Bitcoin"
        assert normalize_entity_name("btc") == "Bitcoin"
        assert normalize_entity_name("bitcoin") == "Bitcoin"
        assert normalize_entity_name("Bitcoin") == "Bitcoin"
    
    def test_normalize_eth_variants(self):
        """Test that all ETH variants normalize to Ethereum."""
        assert normalize_entity_name("ETH") == "Ethereum"
        assert normalize_entity_name("$ETH") == "Ethereum"
        assert normalize_entity_name("eth") == "Ethereum"
    
    def test_normalize_unknown_entity(self):
        """Test that unknown entities are returned unchanged."""
        assert normalize_entity_name("UnknownToken") == "UnknownToken"
        assert normalize_entity_name("$UNKNOWN") == "$UNKNOWN"
    
    def test_normalize_empty_string(self):
        """Test that empty strings are handled."""
        assert normalize_entity_name("") == ""
        assert normalize_entity_name(None) == None


class TestGetCanonicalNames:
    """Tests for get_canonical_names function."""
    
    def test_contains_major_cryptos(self):
        """Test that list contains major cryptocurrencies."""
        canonical_names = get_canonical_names()
        assert "Bitcoin" in canonical_names
        assert "Ethereum" in canonical_names
        assert "Solana" in canonical_names


class TestIsCanonical:
    """Tests for is_canonical function."""
    
    def test_canonical_names(self):
        """Test that canonical names are identified correctly."""
        assert is_canonical("Bitcoin") == True
        assert is_canonical("Ethereum") == True
    
    def test_non_canonical_names(self):
        """Test that non-canonical names return False."""
        assert is_canonical("BTC") == False
        assert is_canonical("$BTC") == False
