"""
Integration tests for batched entity extraction with partial failure handling.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from crypto_news_aggregator.background.rss_fetcher import (
    _process_entity_extraction_batch,
    _normalize_entity,
    _deduplicate_entities,
    _retry_individual_extractions,
)


@pytest.fixture
def sample_10_articles():
    """Generate 10 sample articles for batch testing."""
    articles = []
    for i in range(10):
        articles.append({
            "_id": f"article_{i}",
            "title": f"Test Article {i}",
            "text": f"This is test article {i} about Bitcoin and Ethereum.",
            "content": "",
            "description": "",
        })
    return articles


@pytest.fixture
def mock_llm_client_success():
    """Mock LLM client that successfully processes all articles."""
    client = Mock()
    
    def extract_batch(articles):
        results = []
        for idx, article in enumerate(articles):
            results.append({
                "article_index": idx,
                "article_id": article["id"],
                "entities": [
                    {"type": "ticker", "value": "$btc", "confidence": 0.95},
                    {"type": "project", "value": "bitcoin", "confidence": 0.95},
                    {"type": "event", "value": "REGULATION", "confidence": 0.85},
                ],
                "sentiment": "positive"
            })
        
        return {
            "results": results,
            "usage": {
                "model": "claude-3-5-haiku-20241022",
                "input_tokens": len(articles) * 150,
                "output_tokens": len(articles) * 30,
                "total_tokens": len(articles) * 180,
                "input_cost": len(articles) * 0.00012,
                "output_cost": len(articles) * 0.00012,
                "total_cost": len(articles) * 0.00024,
            }
        }
    
    client.extract_entities_batch = Mock(side_effect=extract_batch)
    return client


@pytest.fixture
def mock_llm_client_partial_failure():
    """Mock LLM client that fails on batch but succeeds on individual retries."""
    client = Mock()
    
    # First call fails (batch)
    # Subsequent calls succeed (individual retries)
    call_count = [0]
    
    def extract_batch(articles):
        call_count[0] += 1
        
        # First call (batch) fails
        if call_count[0] == 1:
            raise Exception("Batch processing failed")
        
        # Individual retries succeed
        results = []
        for idx, article in enumerate(articles):
            results.append({
                "article_index": idx,
                "article_id": article["id"],
                "entities": [
                    {"type": "ticker", "value": "$ETH", "confidence": 0.90},
                ],
                "sentiment": "neutral"
            })
        
        return {
            "results": results,
            "usage": {
                "model": "claude-3-5-haiku-20241022",
                "input_tokens": 150,
                "output_tokens": 30,
                "total_tokens": 180,
                "input_cost": 0.00012,
                "output_cost": 0.00012,
                "total_cost": 0.00024,
            }
        }
    
    client.extract_entities_batch = Mock(side_effect=extract_batch)
    return client


@pytest.mark.asyncio
async def test_batch_processing_10_articles_success(mock_llm_client_success, sample_10_articles):
    """Test successful batch processing of 10 articles."""
    result = await _process_entity_extraction_batch(sample_10_articles, mock_llm_client_success)
    
    # Verify all 10 articles were processed
    assert len(result["results"]) == 10
    assert result["metrics"]["articles_processed"] == 10
    
    # Verify entities were extracted (after normalization and deduplication)
    total_entities = result["metrics"]["entities_extracted"]
    assert total_entities > 0  # Should have entities after deduplication
    
    # Verify cost calculation
    usage = result["usage"]
    assert usage["model"] == "claude-3-5-haiku-20241022"
    assert usage["input_tokens"] == 1500  # 10 articles * 150 tokens
    assert usage["output_tokens"] == 300  # 10 articles * 30 tokens
    assert usage["total_tokens"] == 1800
    assert abs(usage["total_cost"] - 0.0024) < 0.0001  # 10 * 0.00024 (with floating point tolerance)
    
    # Verify processing time was tracked
    assert "processing_time" in result["metrics"]
    assert result["metrics"]["processing_time"] > 0


@pytest.mark.asyncio
async def test_batch_processing_with_normalization(mock_llm_client_success, sample_10_articles):
    """Test that entities are normalized correctly."""
    result = await _process_entity_extraction_batch(sample_10_articles, mock_llm_client_success)
    
    # Check that entities were normalized
    for article_result in result["results"]:
        entities = article_result["entities"]
        
        # Find ticker entity
        ticker_entities = [e for e in entities if e["type"] == "ticker"]
        if ticker_entities:
            # Should be normalized to uppercase with $ prefix
            assert ticker_entities[0]["value"] == "$BTC"
        
        # Find project entity
        project_entities = [e for e in entities if e["type"] == "project"]
        if project_entities:
            # Should be normalized to title case
            assert project_entities[0]["value"] == "Bitcoin"
        
        # Find event entity
        event_entities = [e for e in entities if e["type"] == "event"]
        if event_entities:
            # Should be normalized to lowercase
            assert event_entities[0]["value"] == "regulation"


@pytest.mark.asyncio
async def test_partial_failure_with_retry(mock_llm_client_partial_failure, sample_10_articles):
    """Test partial failure scenario with individual retries."""
    result = await _process_entity_extraction_batch(
        sample_10_articles, 
        mock_llm_client_partial_failure,
        retry_individual=True
    )
    
    # Should have retried individually and succeeded
    assert len(result["results"]) == 10
    assert result["metrics"]["articles_processed"] == 10
    
    # Verify cost was aggregated from individual calls
    usage = result["usage"]
    assert usage["total_cost"] > 0
    
    # Verify processing time was tracked
    assert result["metrics"]["processing_time"] > 0


@pytest.mark.asyncio
async def test_partial_failure_no_retry(mock_llm_client_partial_failure, sample_10_articles):
    """Test partial failure without retry returns empty results."""
    result = await _process_entity_extraction_batch(
        sample_10_articles, 
        mock_llm_client_partial_failure,
        retry_individual=False
    )
    
    # Should return empty results without retry
    assert len(result["results"]) == 0
    assert result["metrics"]["articles_processed"] == 0


@pytest.mark.asyncio
async def test_entity_normalization_tickers():
    """Test ticker normalization."""
    assert _normalize_entity("btc", "ticker") == "$BTC"
    assert _normalize_entity("$btc", "ticker") == "$BTC"
    assert _normalize_entity("$BTC", "ticker") == "$BTC"
    assert _normalize_entity("eth", "ticker") == "$ETH"


@pytest.mark.asyncio
async def test_entity_normalization_projects():
    """Test project name normalization."""
    assert _normalize_entity("bitcoin", "project") == "Bitcoin"
    assert _normalize_entity("Bitcoin", "project") == "Bitcoin"
    assert _normalize_entity("BITCOIN", "project") == "Bitcoin"
    assert _normalize_entity("ethereum", "project") == "Ethereum"
    assert _normalize_entity("solana", "project") == "Solana"
    assert _normalize_entity("unknown project", "project") == "Unknown Project"


@pytest.mark.asyncio
async def test_entity_normalization_events():
    """Test event type normalization."""
    assert _normalize_entity("REGULATION", "event") == "regulation"
    assert _normalize_entity("Regulation", "event") == "regulation"
    assert _normalize_entity("regulation", "event") == "regulation"


@pytest.mark.asyncio
async def test_entity_deduplication():
    """Test entity deduplication with normalization."""
    entities = [
        {"type": "ticker", "value": "$btc", "confidence": 0.90},
        {"type": "ticker", "value": "$BTC", "confidence": 0.95},
        {"type": "ticker", "value": "btc", "confidence": 0.85},
        {"type": "project", "value": "bitcoin", "confidence": 0.90},
        {"type": "project", "value": "Bitcoin", "confidence": 0.95},
        {"type": "event", "value": "REGULATION", "confidence": 0.85},
        {"type": "event", "value": "regulation", "confidence": 0.90},
    ]
    
    deduplicated = _deduplicate_entities(entities)
    
    # Should have 3 unique entities (1 ticker, 1 project, 1 event)
    assert len(deduplicated) == 3
    
    # Check that highest confidence was kept
    ticker = next(e for e in deduplicated if e["type"] == "ticker")
    assert ticker["value"] == "$BTC"
    assert ticker["confidence"] == 0.95
    
    project = next(e for e in deduplicated if e["type"] == "project")
    assert project["value"] == "Bitcoin"
    assert project["confidence"] == 0.95
    
    event = next(e for e in deduplicated if e["type"] == "event")
    assert event["value"] == "regulation"
    assert event["confidence"] == 0.90


@pytest.mark.asyncio
async def test_empty_batch():
    """Test that empty batch returns empty results."""
    mock_client = Mock()
    result = await _process_entity_extraction_batch([], mock_client)
    
    assert result["results"] == []
    assert result["metrics"]["articles_processed"] == 0
    assert result["metrics"]["entities_extracted"] == 0
    mock_client.extract_entities_batch.assert_not_called()


@pytest.mark.asyncio
async def test_batch_metrics_calculation(mock_llm_client_success):
    """Test that batch metrics are calculated correctly."""
    articles = [
        {"_id": "1", "title": "Test 1", "text": "Bitcoin news"},
        {"_id": "2", "title": "Test 2", "text": "Ethereum news"},
    ]
    
    result = await _process_entity_extraction_batch(articles, mock_llm_client_success)
    
    metrics = result["metrics"]
    assert metrics["articles_processed"] == 2
    assert metrics["entities_extracted"] > 0
    assert metrics["processing_time"] > 0
    assert "failed_articles" not in metrics or len(metrics["failed_articles"]) == 0


@pytest.mark.asyncio
async def test_cost_tracking_from_api_response(mock_llm_client_success, sample_10_articles):
    """Test that costs are tracked from actual API response, not estimates."""
    result = await _process_entity_extraction_batch(sample_10_articles, mock_llm_client_success)
    
    usage = result["usage"]
    
    # Verify we're using actual token counts from API
    assert "input_tokens" in usage
    assert "output_tokens" in usage
    assert "total_tokens" in usage
    
    # Verify costs are calculated from actual tokens
    assert usage["input_cost"] > 0
    assert usage["output_cost"] > 0
    assert usage["total_cost"] == usage["input_cost"] + usage["output_cost"]
    
    # Verify model is tracked
    assert usage["model"] == "claude-3-5-haiku-20241022"


@pytest.mark.asyncio
async def test_batch_size_configuration():
    """Test that batch size is configurable via environment variable."""
    from crypto_news_aggregator.core.config import settings
    
    # Verify the setting exists and is configurable
    assert hasattr(settings, "ENTITY_EXTRACTION_BATCH_SIZE")
    assert isinstance(settings.ENTITY_EXTRACTION_BATCH_SIZE, int)
    assert settings.ENTITY_EXTRACTION_BATCH_SIZE == 10  # Default value


@pytest.mark.asyncio
async def test_exact_haiku_model_string():
    """Test that exact Haiku model string is used."""
    from crypto_news_aggregator.core.config import settings
    
    # Verify exact model string
    assert settings.ANTHROPIC_ENTITY_MODEL == "claude-3-5-haiku-20241022"
