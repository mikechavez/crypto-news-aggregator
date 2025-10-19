"""
Tests for narrative matching functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.crypto_news_aggregator.services.narrative_service import find_matching_narrative


@pytest.mark.asyncio
async def test_find_matching_narrative_with_match():
    """Test finding a matching narrative above similarity threshold."""
    # Mock fingerprint to search for
    search_fingerprint = {
        'nucleus_entity': 'SEC',
        'top_actors': ['SEC', 'Binance', 'Coinbase'],
        'key_actions': ['filed lawsuit', 'regulatory enforcement']
    }
    
    # Mock existing narrative with similar fingerprint
    mock_narrative = {
        '_id': 'narrative_123',
        'title': 'SEC Regulatory Actions',
        'last_updated': datetime.now(timezone.utc),
        'status': 'hot',
        'fingerprint': {
            'nucleus_entity': 'SEC',
            'top_actors': ['SEC', 'Binance', 'Kraken'],
            'key_actions': ['filed lawsuit', 'compliance review']
        }
    }
    
    # Mock database
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[mock_narrative])
    
    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    
    mock_db = MagicMock()
    mock_db.narratives = mock_collection
    
    with patch('src.crypto_news_aggregator.services.narrative_service.mongo_manager') as mock_mongo:
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Call function
        result = await find_matching_narrative(search_fingerprint, within_days=14)
        
        # Verify result
        assert result is not None
        assert result['_id'] == 'narrative_123'
        assert result['title'] == 'SEC Regulatory Actions'
        
        # Verify query was constructed correctly
        mock_collection.find.assert_called_once()
        query = mock_collection.find.call_args[0][0]
        assert 'last_updated' in query
        assert '$or' in query
        # Check that query includes status or lifecycle_state filters
        assert any('status' in condition for condition in query['$or'])


@pytest.mark.asyncio
async def test_find_matching_narrative_no_match():
    """Test when no narrative exceeds similarity threshold."""
    # Mock fingerprint to search for
    search_fingerprint = {
        'nucleus_entity': 'Bitcoin',
        'top_actors': ['MicroStrategy', 'Tesla'],
        'key_actions': ['purchased', 'investment']
    }
    
    # Mock existing narrative with low similarity
    mock_narrative = {
        '_id': 'narrative_456',
        'title': 'SEC Regulatory Actions',
        'last_updated': datetime.now(timezone.utc),
        'status': 'hot',
        'fingerprint': {
            'nucleus_entity': 'SEC',
            'top_actors': ['SEC', 'Binance'],
            'key_actions': ['filed lawsuit']
        }
    }
    
    # Mock database
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[mock_narrative])
    
    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    
    mock_db = MagicMock()
    mock_db.narratives = mock_collection
    
    with patch('src.crypto_news_aggregator.services.narrative_service.mongo_manager') as mock_mongo:
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Call function
        result = await find_matching_narrative(search_fingerprint, within_days=14)
        
        # Verify no match found
        assert result is None


@pytest.mark.asyncio
async def test_find_matching_narrative_no_candidates():
    """Test when no candidate narratives exist in time window."""
    search_fingerprint = {
        'nucleus_entity': 'Bitcoin',
        'top_actors': ['MicroStrategy'],
        'key_actions': ['purchased']
    }
    
    # Mock database with no results
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    
    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    
    mock_db = MagicMock()
    mock_db.narratives = mock_collection
    
    with patch('src.crypto_news_aggregator.services.narrative_service.mongo_manager') as mock_mongo:
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Call function
        result = await find_matching_narrative(search_fingerprint, within_days=7)
        
        # Verify no match found
        assert result is None


@pytest.mark.asyncio
async def test_find_matching_narrative_legacy_format():
    """Test matching with legacy narrative format (no fingerprint field)."""
    search_fingerprint = {
        'nucleus_entity': 'DeFi',
        'top_actors': ['Uniswap', 'Aave'],
        'key_actions': ['liquidity', 'governance']
    }
    
    # Mock legacy narrative without fingerprint field
    mock_narrative = {
        '_id': 'narrative_789',
        'title': 'DeFi Protocol Updates',
        'last_updated': datetime.now(timezone.utc),
        'status': 'emerging',
        'theme': 'DeFi',
        'entities': ['Uniswap', 'Aave', 'Compound']
    }
    
    # Mock database
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[mock_narrative])
    
    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    
    mock_db = MagicMock()
    mock_db.narratives = mock_collection
    
    with patch('src.crypto_news_aggregator.services.narrative_service.mongo_manager') as mock_mongo:
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Call function
        result = await find_matching_narrative(search_fingerprint, within_days=14)
        
        # Verify result (should construct fingerprint from legacy fields)
        # Similarity should be high due to matching nucleus and actors
        assert result is not None
        assert result['_id'] == 'narrative_789'


@pytest.mark.asyncio
async def test_find_matching_narrative_custom_time_window():
    """Test with custom time window parameter."""
    search_fingerprint = {
        'nucleus_entity': 'Ethereum',
        'top_actors': ['Vitalik'],
        'key_actions': ['upgrade']
    }
    
    # Mock database
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    
    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    
    mock_db = MagicMock()
    mock_db.narratives = mock_collection
    
    with patch('src.crypto_news_aggregator.services.narrative_service.mongo_manager') as mock_mongo:
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Call function with custom time window
        result = await find_matching_narrative(search_fingerprint, within_days=30)
        
        # Verify query used correct time window
        mock_collection.find.assert_called_once()
        query = mock_collection.find.call_args[0][0]
        
        # Check that cutoff time is approximately 30 days ago
        cutoff = query['last_updated']['$gte']
        expected_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        time_diff = abs((cutoff - expected_cutoff).total_seconds())
        assert time_diff < 5  # Within 5 seconds tolerance


@pytest.mark.asyncio
async def test_find_matching_narrative_adaptive_threshold_recent():
    """Test adaptive threshold: recent narrative (within 48h) uses 0.5 threshold."""
    # Mock fingerprint with moderate similarity (0.52)
    search_fingerprint = {
        'nucleus_entity': 'SEC',
        'top_actors': ['SEC', 'Binance', 'Coinbase'],
        'key_actions': ['filed lawsuit', 'regulatory enforcement']
    }
    
    # Mock recent narrative (updated 24 hours ago) with moderate similarity
    # This should match with 0.5 threshold but not with 0.6 threshold
    mock_narrative = {
        '_id': 'narrative_recent',
        'title': 'SEC Regulatory Actions',
        'last_updated': datetime.now(timezone.utc) - timedelta(hours=24),
        'status': 'hot',
        'fingerprint': {
            'nucleus_entity': 'SEC',
            'top_actors': ['SEC', 'Binance'],  # Slightly different actors
            'key_actions': ['filed lawsuit']  # Fewer actions
        }
    }
    
    # Mock database
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[mock_narrative])
    
    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    
    mock_db = MagicMock()
    mock_db.narratives = mock_collection
    
    with patch('src.crypto_news_aggregator.services.narrative_service.mongo_manager') as mock_mongo:
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Call function
        result = await find_matching_narrative(search_fingerprint, within_days=14)
        
        # Verify match found (0.5 threshold for recent narratives)
        assert result is not None
        assert result['_id'] == 'narrative_recent'


@pytest.mark.asyncio
async def test_find_matching_narrative_adaptive_threshold_old():
    """Test adaptive threshold: old narrative (>48h) uses 0.6 threshold."""
    # Mock fingerprint with moderate similarity (should be between 0.5-0.6)
    search_fingerprint = {
        'nucleus_entity': 'SEC',
        'top_actors': ['SEC', 'Binance', 'Coinbase', 'Kraken', 'Gemini'],
        'key_actions': ['filed lawsuit', 'regulatory enforcement', 'compliance review']
    }
    
    # Mock old narrative (updated 5 days ago) with moderate similarity
    # Different actors and actions to create ~0.5-0.6 similarity
    mock_narrative = {
        '_id': 'narrative_old',
        'title': 'SEC Regulatory Actions',
        'last_updated': datetime.now(timezone.utc) - timedelta(days=5),
        'status': 'cooling',
        'fingerprint': {
            'nucleus_entity': 'SEC',
            'top_actors': ['SEC', 'Ripple'],  # Different actors (only SEC overlaps)
            'key_actions': ['investigation']  # Different action
        }
    }
    
    # Mock database
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[mock_narrative])
    
    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    
    mock_db = MagicMock()
    mock_db.narratives = mock_collection
    
    with patch('src.crypto_news_aggregator.services.narrative_service.mongo_manager') as mock_mongo:
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Call function
        result = await find_matching_narrative(search_fingerprint, within_days=14)
        
        # Verify no match found (0.6 threshold for old narratives)
        # Note: If similarity happens to be >0.6, this test may need adjustment
        assert result is None


@pytest.mark.asyncio
async def test_find_matching_narrative_adaptive_threshold_boundary():
    """Test adaptive threshold at 48-hour boundary."""
    search_fingerprint = {
        'nucleus_entity': 'Bitcoin',
        'top_actors': ['MicroStrategy', 'Tesla'],
        'key_actions': ['purchased']
    }
    
    # Mock narrative exactly at 48-hour boundary
    mock_narrative_boundary = {
        '_id': 'narrative_boundary',
        'title': 'Bitcoin Purchases',
        'last_updated': datetime.now(timezone.utc) - timedelta(hours=48),
        'status': 'emerging',
        'fingerprint': {
            'nucleus_entity': 'Bitcoin',
            'top_actors': ['MicroStrategy'],
            'key_actions': ['purchased']
        }
    }
    
    # Mock database
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[mock_narrative_boundary])
    
    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=mock_cursor)
    
    mock_db = MagicMock()
    mock_db.narratives = mock_collection
    
    with patch('src.crypto_news_aggregator.services.narrative_service.mongo_manager') as mock_mongo:
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Call function
        result = await find_matching_narrative(search_fingerprint, within_days=14)
        
        # At exactly 48 hours, should use 0.6 threshold (older narrative)
        # High similarity should still match
        assert result is not None
