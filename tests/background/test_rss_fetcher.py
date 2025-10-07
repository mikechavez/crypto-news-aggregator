import asyncio
from datetime import datetime, timezone

import pytest

from src.crypto_news_aggregator.background import rss_fetcher
from src.crypto_news_aggregator.services.rss_service import RSSService
from src.crypto_news_aggregator.models.article import (
    ArticleCreate,
    ArticleMetrics,
    ArticleAuthor,
)


class FakeLLMProvider:
    def __init__(self, relevance: float = 0.8, sentiment: float = 0.6, themes=None):
        self._relevance = relevance
        self._sentiment = sentiment
        self._themes = themes or ["Bitcoin", "Market"]

    def analyze_sentiment(self, text: str) -> float:
        return self._sentiment

    def extract_themes(self, texts):
        return self._themes

    def generate_insight(self, data):
        raise NotImplementedError

    def score_relevance(self, text: str) -> float:
        return self._relevance


class FakeRSSService:
    def __init__(self, articles):
        self._articles = articles

    async def fetch_all_feeds(self):
        await asyncio.sleep(0)
        return self._articles


@pytest.mark.asyncio
async def test_process_new_articles_from_mongodb_enriches_articles(
    mongo_db, monkeypatch
):
    monkeypatch.setattr(
        rss_fetcher,
        "get_llm_provider",
        lambda: FakeLLMProvider(themes=["ETFs", "Institutional"]),
    )

    await mongo_db.articles.delete_many({})
    article_doc = {
        "title": "BTC surges as ETFs see inflows",
        "source_id": "test-article-1",
        "source": "rss",
        "text": "Bitcoin rallied above $70k amid renewed ETF demand.",
        "author": None,
        "url": "https://example.com/btc-surges",
        "lang": "en",
        "metrics": ArticleMetrics().model_dump(),
        "keywords": [],
        "relevance_score": None,
        "sentiment_score": None,
        "sentiment_label": None,
        "raw_data": {},
        "published_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    insert_result = await mongo_db.articles.insert_one(article_doc)

    await rss_fetcher.process_new_articles_from_mongodb()

    # Wait a bit for enrichment to complete
    await asyncio.sleep(0.1)

    stored = await mongo_db.articles.find_one({"source_id": "test-article-1"})
    assert stored is not None
    assert stored["relevance_score"] == pytest.approx(0.8)
    assert stored["sentiment_score"] == pytest.approx(0.6)
    assert stored["sentiment_label"] == "positive"
    assert stored["themes"] == ["ETFs", "Institutional"]


@pytest.mark.asyncio
async def test_fetch_and_process_rss_feeds_persists_and_enriches(mongo_db, monkeypatch):
    monkeypatch.setattr(
        rss_fetcher,
        "get_llm_provider",
        lambda: FakeLLMProvider(themes=["ETFs", "Institutional"]),
    )
    await mongo_db.articles.delete_many({})

    article = ArticleCreate(
        title="Institutional flows drive crypto rally",
        source_id="test-article-2",
        source="rss",
        text="Large investors poured capital into Bitcoin ETFs, lifting prices.",
        author=None,
        url="https://example.com/etf-flows",
        lang="en",
        metrics=ArticleMetrics(),
        keywords=[],
        relevance_score=None,
        sentiment_score=None,
        sentiment_label=None,
        raw_data={},
        published_at=datetime.now(timezone.utc),
    )

    from src.crypto_news_aggregator.services import rss_service

    monkeypatch.setattr(rss_service, "RSSService", lambda: FakeRSSService([article]))

    await rss_fetcher.fetch_and_process_rss_feeds()

    # Wait a bit for enrichment to complete
    await asyncio.sleep(0.1)

    stored = await mongo_db.articles.find_one({"source_id": "test-article-2"})
    assert stored is not None
    assert stored["relevance_score"] == pytest.approx(0.8)
    assert stored["sentiment_score"] == pytest.approx(0.6)
    assert stored["sentiment_label"] == "positive"
    assert stored["themes"] == ["ETFs", "Institutional"]


def test_rss_service_has_correct_feed_count():
    """Verify that RSSService has the expected number of RSS feeds configured."""
    rss_service = RSSService()
    
    # Should have 13 total feeds:
    # - 4 original (coindesk, cointelegraph, decrypt, bitcoinmagazine)
    # - 6 News & General (theblock, cryptoslate, benzinga, bitcoincom, dlnews, watcherguru)
    # - 2 Research & Analysis (glassnode, messari)
    # - 1 DeFi-Focused (thedefiant)
    assert len(rss_service.feed_urls) == 13, f"Expected 13 RSS feeds, got {len(rss_service.feed_urls)}"
    
    # Verify key sources are present
    expected_sources = [
        "coindesk", "cointelegraph", "decrypt", "bitcoinmagazine",  # Original
        "theblock", "cryptoslate", "benzinga", "bitcoincom", "dlnews", "watcherguru",  # News & General
        "glassnode", "messari",  # Research
        "thedefiant",  # DeFi
    ]
    
    for source in expected_sources:
        assert source in rss_service.feed_urls, f"Expected source '{source}' not found in feed_urls"
    
    # Verify all URLs are valid strings
    for source, url in rss_service.feed_urls.items():
        assert isinstance(url, str), f"URL for {source} is not a string"
        assert url.startswith("http"), f"URL for {source} does not start with http"
