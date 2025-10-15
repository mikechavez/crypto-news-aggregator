"""
Tests for narrative detection with matching functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

from src.crypto_news_aggregator.services.narrative_service import detect_narratives


@pytest.mark.asyncio
async def test_detect_narratives_merges_into_existing():
    """Test that detect_narratives merges new articles into existing matching narratives."""
    
    # Mock articles with narrative data
    mock_articles = [
        {
            '_id': ObjectId(),
            'title': 'SEC sues Binance',
            'published_at': datetime.now(timezone.utc) - timedelta(hours=2),
            'narrative_summary': {
                'nucleus_entity': 'SEC',
                'actors': {'SEC': 5, 'Binance': 4},
                'actions': ['filed lawsuit'],
                'tensions': ['regulatory enforcement']
            }
        },
        {
            '_id': ObjectId(),
            'title': 'SEC charges Coinbase',
            'published_at': datetime.now(timezone.utc) - timedelta(hours=1),
            'narrative_summary': {
                'nucleus_entity': 'SEC',
                'actors': {'SEC': 5, 'Coinbase': 4},
                'actions': ['filed charges'],
                'tensions': ['regulatory enforcement']
            }
        }
    ]
    
    # Mock existing narrative that should match
    existing_narrative = {
        '_id': ObjectId(),
        'title': 'SEC Regulatory Crackdown',
        'summary': 'SEC taking enforcement actions',
        'article_ids': ['old_article_1', 'old_article_2'],
        'article_count': 2,
        'last_updated': datetime.now(timezone.utc) - timedelta(days=3),
        'status': 'hot',
        'fingerprint': {
            'nucleus_entity': 'SEC',
            'top_actors': ['SEC', 'Binance'],
            'key_actions': ['enforcement']
        }
    }
    
    # Mock cluster result
    mock_cluster = {
        'nucleus_entity': 'SEC',
        'actors': {'SEC': 5, 'Binance': 4, 'Coinbase': 4},
        'actions': ['filed lawsuit', 'filed charges'],
        'article_ids': [str(mock_articles[0]['_id']), str(mock_articles[1]['_id'])],
        'article_count': 2
    }
    
    # Setup mocks
    with patch('src.crypto_news_aggregator.services.narrative_service.backfill_narratives_for_recent_articles') as mock_backfill, \
         patch('src.crypto_news_aggregator.services.narrative_service.mongo_manager') as mock_mongo, \
         patch('src.crypto_news_aggregator.services.narrative_service.cluster_by_narrative_salience') as mock_cluster_fn, \
         patch('src.crypto_news_aggregator.services.narrative_service.compute_narrative_fingerprint') as mock_fingerprint, \
         patch('src.crypto_news_aggregator.services.narrative_service.find_matching_narrative') as mock_find_match:
        
        # Configure mocks
        mock_backfill.return_value = 2
        
        # Mock database
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_articles)
        
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_collection.update_one = AsyncMock()
        
        mock_db = MagicMock()
        mock_db.articles = mock_collection
        mock_db.narratives = mock_collection
        
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Mock clustering
        mock_cluster_fn.return_value = [mock_cluster]
        
        # Mock fingerprint computation
        mock_fingerprint.return_value = {
            'nucleus_entity': 'SEC',
            'top_actors': ['SEC', 'Binance', 'Coinbase'],
            'key_actions': ['filed lawsuit', 'filed charges'],
            'timestamp': datetime.now(timezone.utc)
        }
        
        # Mock finding matching narrative
        mock_find_match.return_value = existing_narrative
        
        # Call detect_narratives
        result = await detect_narratives(hours=48, min_articles=2, use_salience_clustering=True)
        
        # Verify that update_one was called to merge articles
        assert mock_collection.update_one.called
        update_call = mock_collection.update_one.call_args
        
        # Verify the update included new article_ids
        update_data = update_call[0][1]['$set']
        assert 'article_ids' in update_data
        assert 'needs_summary_update' in update_data
        assert update_data['needs_summary_update'] is True
        assert len(update_data['article_ids']) > 2  # Should have combined old + new


@pytest.mark.asyncio
async def test_detect_narratives_creates_new_when_no_match():
    """Test that detect_narratives creates new narrative when no match found."""
    
    # Mock articles with narrative data
    mock_articles = [
        {
            '_id': ObjectId(),
            'title': 'Bitcoin ETF approval',
            'published_at': datetime.now(timezone.utc) - timedelta(hours=2),
            'narrative_summary': {
                'nucleus_entity': 'Bitcoin',
                'actors': {'SEC': 5, 'BlackRock': 4},
                'actions': ['approved ETF'],
                'tensions': ['institutional adoption']
            }
        }
    ]
    
    mock_cluster = {
        'nucleus_entity': 'Bitcoin',
        'actors': {'SEC': 5, 'BlackRock': 4},
        'actions': ['approved ETF'],
        'article_ids': [str(mock_articles[0]['_id'])],
        'article_count': 1
    }
    
    mock_narrative = {
        'title': 'Bitcoin ETF Approval',
        'summary': 'SEC approves Bitcoin ETF',
        'nucleus_entity': 'Bitcoin',
        'actors': ['SEC', 'BlackRock'],
        'article_ids': [str(mock_articles[0]['_id'])],
        'article_count': 1,
        'entity_relationships': []
    }
    
    # Setup mocks
    with patch('src.crypto_news_aggregator.services.narrative_service.backfill_narratives_for_recent_articles') as mock_backfill, \
         patch('src.crypto_news_aggregator.services.narrative_service.mongo_manager') as mock_mongo, \
         patch('src.crypto_news_aggregator.services.narrative_service.cluster_by_narrative_salience') as mock_cluster_fn, \
         patch('src.crypto_news_aggregator.services.narrative_service.compute_narrative_fingerprint') as mock_fingerprint, \
         patch('src.crypto_news_aggregator.services.narrative_service.find_matching_narrative') as mock_find_match, \
         patch('src.crypto_news_aggregator.services.narrative_service.generate_narrative_from_cluster') as mock_generate:
        
        # Configure mocks
        mock_backfill.return_value = 1
        
        # Mock database
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_articles)
        
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
        
        mock_db = MagicMock()
        mock_db.articles = mock_collection
        mock_db.narratives = mock_collection
        
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        
        # Mock clustering
        mock_cluster_fn.return_value = [mock_cluster]
        
        # Mock fingerprint computation
        mock_fingerprint.return_value = {
            'nucleus_entity': 'Bitcoin',
            'top_actors': ['SEC', 'BlackRock'],
            'key_actions': ['approved ETF'],
            'timestamp': datetime.now(timezone.utc)
        }
        
        # Mock no matching narrative found
        mock_find_match.return_value = None
        
        # Mock narrative generation
        mock_generate.return_value = mock_narrative
        
        # Call detect_narratives
        result = await detect_narratives(hours=48, min_articles=1, use_salience_clustering=True)
        
        # Verify that insert_one was called to create new narrative
        assert mock_collection.insert_one.called
        insert_call = mock_collection.insert_one.call_args
        
        # Verify the inserted document has fingerprint and needs_summary_update=False
        inserted_doc = insert_call[0][0]
        assert 'fingerprint' in inserted_doc
        assert 'needs_summary_update' in inserted_doc
        assert inserted_doc['needs_summary_update'] is False


@pytest.mark.asyncio
async def test_detect_narratives_includes_fingerprint_in_new_narratives():
    """Test that new narratives include the computed fingerprint."""
    
    mock_articles = [
        {
            '_id': ObjectId(),
            'title': 'DeFi protocol hack',
            'published_at': datetime.now(timezone.utc) - timedelta(hours=1),
            'narrative_summary': {
                'nucleus_entity': 'Curve',
                'actors': {'Curve': 5, 'Hacker': 4},
                'actions': ['exploited vulnerability'],
                'tensions': ['security breach']
            }
        }
    ]
    
    mock_cluster = {
        'nucleus_entity': 'Curve',
        'actors': {'Curve': 5, 'Hacker': 4},
        'actions': ['exploited vulnerability'],
        'article_ids': [str(mock_articles[0]['_id'])],
        'article_count': 1
    }
    
    mock_narrative = {
        'title': 'Curve Protocol Exploit',
        'summary': 'Curve protocol suffers security breach',
        'nucleus_entity': 'Curve',
        'actors': ['Curve', 'Hacker'],
        'article_ids': [str(mock_articles[0]['_id'])],
        'article_count': 1,
        'entity_relationships': []
    }
    
    expected_fingerprint = {
        'nucleus_entity': 'Curve',
        'top_actors': ['Curve', 'Hacker'],
        'key_actions': ['exploited vulnerability'],
        'timestamp': datetime.now(timezone.utc)
    }
    
    # Setup mocks
    with patch('src.crypto_news_aggregator.services.narrative_service.backfill_narratives_for_recent_articles') as mock_backfill, \
         patch('src.crypto_news_aggregator.services.narrative_service.mongo_manager') as mock_mongo, \
         patch('src.crypto_news_aggregator.services.narrative_service.cluster_by_narrative_salience') as mock_cluster_fn, \
         patch('src.crypto_news_aggregator.services.narrative_service.compute_narrative_fingerprint') as mock_fingerprint, \
         patch('src.crypto_news_aggregator.services.narrative_service.find_matching_narrative') as mock_find_match, \
         patch('src.crypto_news_aggregator.services.narrative_service.generate_narrative_from_cluster') as mock_generate:
        
        mock_backfill.return_value = 1
        
        # Mock database
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_articles)
        
        mock_collection = MagicMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)
        mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
        
        mock_db = MagicMock()
        mock_db.articles = mock_collection
        mock_db.narratives = mock_collection
        
        mock_mongo.get_async_database = AsyncMock(return_value=mock_db)
        mock_cluster_fn.return_value = [mock_cluster]
        mock_fingerprint.return_value = expected_fingerprint
        mock_find_match.return_value = None
        mock_generate.return_value = mock_narrative
        
        # Call detect_narratives
        await detect_narratives(hours=48, min_articles=1, use_salience_clustering=True)
        
        # Verify fingerprint was included in inserted document
        assert mock_collection.insert_one.called
        inserted_doc = mock_collection.insert_one.call_args[0][0]
        assert inserted_doc['fingerprint'] == expected_fingerprint
