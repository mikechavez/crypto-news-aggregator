"""
Tests for batched entity extraction in RSS enrichment pipeline.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from crypto_news_aggregator.background.rss_fetcher import (
    _process_entity_extraction_batch,
    process_new_articles_from_mongodb,
)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client with entity extraction support."""
    client = Mock()
    client.extract_entities_batch = Mock(return_value={
        "results": [
            {
                "article_index": 0,
                "article_id": "article_1",
                "entities": [
                    {"type": "ticker", "value": "$BTC", "confidence": 0.95},
                    {"type": "project", "value": "Bitcoin", "confidence": 0.95},
                    {"type": "event", "value": "regulation", "confidence": 0.85},
                ],
                "sentiment": "negative"
            },
            {
                "article_index": 1,
                "article_id": "article_2",
                "entities": [
                    {"type": "ticker", "value": "$ETH", "confidence": 0.90},
                    {"type": "project", "value": "Ethereum", "confidence": 0.90},
                    {"type": "event", "value": "upgrade", "confidence": 0.88},
                ],
                "sentiment": "positive"
            }
        ],
        "usage": {
            "model": "claude-haiku-3-5-20241022",
            "input_tokens": 1500,
            "output_tokens": 300,
            "total_tokens": 1800,
            "input_cost": 0.0015,
            "output_cost": 0.0003,
            "total_cost": 0.0018,
        }
    })
    return client


@pytest.fixture
def sample_articles():
    """Sample articles for testing."""
    return [
        {
            "_id": "article_1",
            "title": "SEC Announces New Bitcoin Regulations",
            "text": "The Securities and Exchange Commission announced new regulations for Bitcoin trading.",
            "content": "",
            "description": "",
        },
        {
            "_id": "article_2",
            "title": "Ethereum Upgrade Successfully Deployed",
            "text": "The Ethereum network successfully deployed its latest upgrade, improving scalability.",
            "content": "",
            "description": "",
        }
    ]


@pytest.mark.asyncio
async def test_process_entity_extraction_batch_success(mock_llm_client, sample_articles):
    """Test successful batch entity extraction."""
    result = await _process_entity_extraction_batch(sample_articles, mock_llm_client)
    
    # Verify the LLM client was called
    mock_llm_client.extract_entities_batch.assert_called_once()
    
    # Verify the call arguments
    call_args = mock_llm_client.extract_entities_batch.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0]["id"] == "article_1"
    assert call_args[1]["id"] == "article_2"
    
    # Verify results
    assert "results" in result
    assert "usage" in result
    assert len(result["results"]) == 2
    assert result["usage"]["total_cost"] == 0.0018


@pytest.mark.asyncio
async def test_process_entity_extraction_batch_empty():
    """Test batch processing with empty articles list."""
    mock_client = Mock()
    result = await _process_entity_extraction_batch([], mock_client)
    
    assert result["results"] == []
    assert result["usage"] == {}
    assert result["metrics"]["articles_processed"] == 0
    assert result["metrics"]["entities_extracted"] == 0
    mock_client.extract_entities_batch.assert_not_called()


@pytest.mark.asyncio
async def test_process_entity_extraction_batch_truncates_long_text(mock_llm_client):
    """Test that long article text is truncated."""
    long_article = {
        "_id": "long_article",
        "title": "Long Article",
        "text": "A" * 3000,  # Very long text
        "content": "",
        "description": "",
    }
    
    await _process_entity_extraction_batch([long_article], mock_llm_client)
    
    # Verify the text was truncated
    call_args = mock_llm_client.extract_entities_batch.call_args[0][0]
    assert len(call_args[0]["text"]) <= 2003  # 2000 + "..."


@pytest.mark.asyncio
async def test_process_entity_extraction_batch_handles_exception(mock_llm_client):
    """Test that exceptions during extraction are handled gracefully."""
    mock_llm_client.extract_entities_batch.side_effect = Exception("API Error")
    
    result = await _process_entity_extraction_batch([{"_id": "test", "title": "Test", "text": "Test"}], mock_llm_client, retry_individual=False)
    
    assert result["results"] == []
    assert result["usage"] == {}
    assert result["metrics"]["articles_processed"] == 0


@pytest.mark.asyncio
async def test_entity_extraction_cost_tracking(mock_llm_client, sample_articles):
    """Test that cost tracking is properly calculated."""
    result = await _process_entity_extraction_batch(sample_articles, mock_llm_client)
    
    usage = result["usage"]
    assert usage["model"] == "claude-haiku-3-5-20241022"
    assert usage["input_tokens"] == 1500
    assert usage["output_tokens"] == 300
    assert usage["total_tokens"] == 1800
    assert usage["input_cost"] == 0.0015
    assert usage["output_cost"] == 0.0003
    assert usage["total_cost"] == 0.0018


@pytest.mark.asyncio
async def test_entity_types_extracted(mock_llm_client, sample_articles):
    """Test that all entity types are properly extracted."""
    result = await _process_entity_extraction_batch(sample_articles, mock_llm_client)
    
    # Check first article entities
    article_1_entities = result["results"][0]["entities"]
    entity_types = {e["type"] for e in article_1_entities}
    assert "ticker" in entity_types
    assert "project" in entity_types
    assert "event" in entity_types
    
    # Check entity values
    entity_values = {e["value"] for e in article_1_entities}
    assert "$BTC" in entity_values
    assert "Bitcoin" in entity_values
    assert "regulation" in entity_values


@pytest.mark.asyncio
async def test_entity_confidence_scores(mock_llm_client, sample_articles):
    """Test that confidence scores are included in entity extraction."""
    result = await _process_entity_extraction_batch(sample_articles, mock_llm_client)
    
    for article_result in result["results"]:
        for entity in article_result["entities"]:
            assert "confidence" in entity
            assert 0.0 <= entity["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_sentiment_per_article(mock_llm_client, sample_articles):
    """Test that sentiment is extracted for each article."""
    result = await _process_entity_extraction_batch(sample_articles, mock_llm_client)
    
    assert result["results"][0]["sentiment"] == "negative"
    assert result["results"][1]["sentiment"] == "positive"


@pytest.mark.asyncio
async def test_batch_size_configuration():
    """Test that batch size is configurable via settings."""
    from crypto_news_aggregator.core.config import settings
    
    # Verify the setting exists and has a reasonable default
    assert hasattr(settings, "ENTITY_EXTRACTION_BATCH_SIZE")
    assert settings.ENTITY_EXTRACTION_BATCH_SIZE == 10


@pytest.mark.asyncio
async def test_entity_model_configuration():
    """Test that entity extraction model is configurable."""
    from crypto_news_aggregator.core.config import settings
    
    # Verify the model setting exists
    assert hasattr(settings, "ANTHROPIC_ENTITY_MODEL")
    assert settings.ANTHROPIC_ENTITY_MODEL == "claude-haiku-3-5-20241022"


@pytest.mark.asyncio
async def test_entity_cost_configuration():
    """Test that entity extraction costs are configurable."""
    from crypto_news_aggregator.core.config import settings
    
    # Verify cost settings exist
    assert hasattr(settings, "ANTHROPIC_ENTITY_INPUT_COST_PER_1K_TOKENS")
    assert hasattr(settings, "ANTHROPIC_ENTITY_OUTPUT_COST_PER_1K_TOKENS")
