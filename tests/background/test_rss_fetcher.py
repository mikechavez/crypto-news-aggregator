import asyncio
from datetime import datetime, timezone

import pytest

from src.crypto_news_aggregator.background import rss_fetcher
from src.crypto_news_aggregator.models.article import ArticleCreate, ArticleMetrics


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
async def test_process_new_articles_from_mongodb_enriches_articles(mongo_db, monkeypatch):
    monkeypatch.setattr(rss_fetcher, "get_llm_provider", lambda: FakeLLMProvider())

    await mongo_db.articles.delete_many({})
    article_doc = {
        "title": "BTC surges as ETFs see inflows",
        "text": "Bitcoin rallied above $70k amid renewed ETF demand.",
        "source": "rss",
        "source_id": "test-article-1",
        "url": "https://example.com/btc-surges",
        "lang": "en",
        "metrics": ArticleMetrics().model_dump(),
        "keywords": [],
        "relevance_score": None,
        "sentiment_score": None,
        "sentiment_label": None,
        "themes": [],
        "raw_data": {},
        "published_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    insert_result = await mongo_db.articles.insert_one(article_doc)

    await rss_fetcher.process_new_articles_from_mongodb()

    stored = await mongo_db.articles.find_one({"_id": insert_result.inserted_id})
    assert stored["relevance_score"] == pytest.approx(0.8)
    assert stored["sentiment_score"] == pytest.approx(0.6)
    assert stored["sentiment_label"] == "positive"
    assert stored["themes"] == ["Bitcoin", "Market"]


@pytest.mark.asyncio
async def test_fetch_and_process_rss_feeds_persists_and_enriches(mongo_db, monkeypatch):
    monkeypatch.setattr(rss_fetcher, "get_llm_provider", lambda: FakeLLMProvider(themes=["ETFs", "Institutional"]))

    await mongo_db.articles.delete_many({})

    article = ArticleCreate(
        title="Institutional flows drive crypto rally",
        text="Large investors poured capital into Bitcoin ETFs, lifting prices.",
        url="https://example.com/etf-flows",
        source_id="test-article-2",
        source="rss",
        author=None,
        metrics=ArticleMetrics(),
        raw_data={},
        published_at=datetime.now(timezone.utc),
    )

    monkeypatch.setattr(
        rss_fetcher,
        "RSSService",
        lambda: FakeRSSService([article]),
    )

    await rss_fetcher.fetch_and_process_rss_feeds()

    stored = await mongo_db.articles.find_one({"source_id": "test-article-2"})
    assert stored is not None
    assert stored["relevance_score"] == pytest.approx(0.8)
    assert stored["sentiment_score"] == pytest.approx(0.6)
    assert stored["sentiment_label"] == "positive"
    assert stored["themes"] == ["ETFs", "Institutional"]
