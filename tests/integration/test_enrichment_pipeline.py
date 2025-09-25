"""
Integration tests for the enrichment pipeline.
Tests the interaction between RSS fetcher, database, and LLM services.
"""
import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.crypto_news_aggregator.background.rss_fetcher import (
    process_new_articles_from_mongodb,
    fetch_and_process_rss_feeds
)
from src.crypto_news_aggregator.models.article import ArticleCreate, ArticleMetrics


@pytest.mark.integration
class TestEnrichmentPipelineIntegration:
    """Integration tests for the enrichment pipeline."""

    @pytest.mark.asyncio
    async def test_full_enrichment_pipeline_with_real_database(self, mongo_db):
        """Test the complete enrichment pipeline using real database connection."""
        # Clear existing data
        await mongo_db.articles.delete_many({})

        # Insert multiple articles with missing enrichment fields
        articles_data = [
            {
                "title": "Bitcoin Breaks $70K Resistance",
                "text": "Bitcoin has broken through the $70,000 resistance level amid institutional adoption.",
                "content": "Major institutions continue to show interest in cryptocurrency investments.",
                "description": "BTC price surges past key resistance",
                "source": "integration-test",
                "source_id": "integration-test-1",
                "url": "https://example.com/btc-70k",
                "lang": "en",
                "metrics": ArticleMetrics().model_dump(),
                "keywords": [],
                "relevance_score": None,
                "sentiment_score": None,
                "sentiment_label": None,
                "themes": [],
                "raw_data": {},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "title": "Ethereum Merge Completed Successfully",
                "text": "The Ethereum network has successfully completed the merge to proof-of-stake.",
                "content": "Energy consumption reduced by 99% after the transition.",
                "description": "ETH merge successful",
                "source": "integration-test",
                "source_id": "integration-test-2",
                "url": "https://example.com/eth-merge",
                "lang": "en",
                "metrics": ArticleMetrics().model_dump(),
                "keywords": [],
                "relevance_score": None,
                "sentiment_score": None,
                "sentiment_label": None,
                "themes": [],
                "raw_data": {},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ]

        # Insert test articles
        await mongo_db.articles.insert_many(articles_data)

        # Mock LLM provider with realistic responses
        mock_llm = Mock()
        def mock_score_relevance(text: str) -> float:
            if "Bitcoin" in text:
                return 0.9
            elif "Ethereum" in text:
                return 0.8
            return 0.5

        def mock_analyze_sentiment(text: str) -> float:
            if "surges" in text or "breaks" in text:
                return 0.7
            elif "successfully" in text:
                return 0.6
            return 0.0

        def mock_extract_themes(texts):
            themes = []
            for text in texts:
                if "Bitcoin" in text:
                    themes.extend(["Bitcoin", "Price Action", "Resistance"])
                elif "Ethereum" in text:
                    themes.extend(["Ethereum", "Merge", "Proof-of-Stake"])
            return themes

        mock_llm.score_relevance.side_effect = mock_score_relevance
        mock_llm.analyze_sentiment.side_effect = mock_analyze_sentiment
        mock_llm.extract_themes.side_effect = mock_extract_themes
        # Ensure model_name attribute exists and is a string
        mock_llm.model_name = "test-llm-provider"

        with patch('src.crypto_news_aggregator.background.rss_fetcher.get_llm_provider', return_value=mock_llm):
            # Process articles
            processed_count = await process_new_articles_from_mongodb()

            # Should have processed 2 articles
            assert processed_count == 2

            # Verify first article (Bitcoin)
            btc_article = await mongo_db.articles.find_one({"source_id": "integration-test-1"})
            assert btc_article is not None
            assert btc_article["relevance_score"] == 0.9
            assert btc_article["sentiment_score"] == 0.7
            assert btc_article["sentiment_label"] == "positive"
            assert "Bitcoin" in str(btc_article.get("themes", []))

            # Verify second article (Ethereum)
            eth_article = await mongo_db.articles.find_one({"source_id": "integration-test-2"})
            assert eth_article is not None
            assert eth_article["relevance_score"] == 0.8
            assert eth_article["sentiment_score"] == 0.6
            assert eth_article["sentiment_label"] == "positive"
            assert "Ethereum" in str(eth_article.get("themes", []))

    @pytest.mark.asyncio
    async def test_enrichment_pipeline_handles_mixed_content_types(self, mongo_db):
        """Test enrichment with different types of article content."""
        await mongo_db.articles.delete_many({})

        # Test articles with different content structures
        test_cases = [
            {
                "title": "",  # Empty title
                "text": None,
                "content": None,
                "description": None,
                "expected_processed": False  # Should be skipped due to no content
            },
            {
                "title": "Title with Description",
                "text": None,
                "content": None,
                "description": "This article has only a description with important information about crypto trends.",
                "expected_processed": True
            },
            {
                "title": "Full Article",
                "text": "This is the main article text with detailed information.",
                "content": "Additional content from the full article body.",
                "description": "Brief description",
                "expected_processed": True
            }
        ]

        # Insert test articles
        for i, case in enumerate(test_cases):
            article_doc = {
                "title": case["title"],
                "text": case["text"],
                "content": case["content"],
                "description": case["description"],
                "source": "integration-test",
                "source_id": f"mixed-content-{i}",
                "url": f"https://example.com/mixed-{i}",
                "lang": "en",
                "metrics": ArticleMetrics().model_dump(),
                "keywords": [],
                "relevance_score": None,
                "sentiment_score": None,
                "sentiment_label": None,
                "themes": [],
                "raw_data": {},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            await mongo_db.articles.insert_one(article_doc)

        # Mock LLM provider
        mock_llm = Mock()
        mock_llm.score_relevance.return_value = 0.7
        mock_llm.analyze_sentiment.return_value = 0.3
        mock_llm.extract_themes.return_value = ["Testing"]

        with patch('src.crypto_news_aggregator.background.rss_fetcher.get_llm_provider', return_value=mock_llm):
            processed_count = await process_new_articles_from_mongodb()

            # Should have processed 2 articles (skipping the one with no content)
            assert processed_count == 2

            # Verify the articles that should have been processed
            for i, case in enumerate(test_cases):
                if case["expected_processed"]:
                    article = await mongo_db.articles.find_one({"source_id": f"mixed-content-{i}"})
                    assert article is not None
                    assert article["relevance_score"] == 0.7
                    assert article["sentiment_score"] == 0.3
                    assert article["sentiment_label"] == "neutral"

    @pytest.mark.asyncio
    async def test_enrichment_pipeline_with_keyword_extraction(self, mongo_db):
        """Test that keyword extraction works properly in the enrichment pipeline."""
        await mongo_db.articles.delete_many({})

        # Insert article with rich content for keyword extraction
        article_doc = {
            "title": "DeFi Protocol Launches New Yield Farming Strategies",
            "text": "The decentralized finance protocol has introduced innovative yield farming mechanisms that offer higher returns for liquidity providers. Users can now stake governance tokens to earn additional rewards.",
            "content": "The new yield farming strategies include automated market making, liquidity mining, and governance token staking. These features are designed to attract more users to the platform.",
            "description": "DeFi protocol introduces new yield farming features",
            "source": "integration-test",
            "source_id": "keyword-test-1",
            "url": "https://example.com/defi-yield-farming",
            "lang": "en",
            "metrics": ArticleMetrics().model_dump(),
            "keywords": [],
            "raw_data": {},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await mongo_db.articles.insert_one(article_doc)
        mock_llm = Mock()
        mock_llm.score_relevance.return_value = 0.8
        mock_llm.analyze_sentiment.return_value = 0.5
        mock_llm.extract_themes.return_value = ["DeFi", "Yield Farming", "Liquidity"]

        with patch('src.crypto_news_aggregator.background.rss_fetcher.get_llm_provider', return_value=mock_llm):
            processed_count = await process_new_articles_from_mongodb()

            assert processed_count == 1

            # Verify enrichment
            enriched = await mongo_db.articles.find_one({"source_id": "keyword-test-1"})
            assert enriched is not None
            assert enriched["relevance_score"] == 0.8
            assert enriched["sentiment_score"] == 0.5
            assert enriched["sentiment_label"] == "positive"

            # Verify themes were merged with keywords
            themes = enriched.get("themes", [])
            assert "DeFi" in themes
            assert "Yield Farming" in themes
            assert "Liquidity" in themes
