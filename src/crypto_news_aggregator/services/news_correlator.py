"""
News correlation service to find relevant news articles for price movements.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from ..models.article import ArticleInDB
from ..db.mongodb import mongo_manager, COLLECTION_ARTICLES
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class NewsCorrelator:
    """Service for correlating news articles with price movements."""

    def __init__(self):
        self.bitcoin_keywords = [
            "bitcoin",
            "btc",
            "crypto",
            "cryptocurrency",
            "digital currency",
            "blockchain",
            "satoshi",
            "halving",
            "mining",
            "hash rate",
            "digital gold",
            "store of value",
            "crypto market",
        ]
        self.price_keywords = [
            "price",
            "surge",
            "plunge",
            "rally",
            "crash",
            "drop",
            "rise",
            "fall",
            "soar",
            "tumble",
            "decline",
            "increase",
            "decrease",
            "pump",
            "dump",
            "bull",
            "bear",
            "bullish",
            "bearish",
            "ATH",
            "all-time high",
            "support",
            "resistance",
            "breakout",
            "break down",
        ]
        self.recent_hours = 24  # Consider articles from last 24 hours

    async def _get_collection(self):
        """Get the MongoDB collection for articles."""
        if not hasattr(self, "_collection"):
            self._collection = await mongo_manager.get_async_collection(
                COLLECTION_ARTICLES
            )
        return self._collection

    async def get_recent_articles(self, hours: int = None) -> List[ArticleInDB]:
        """
        Get recent articles from the database.

        Args:
            hours: Number of hours to look back for articles

        Returns:
            List[ArticleInDB]: List of recent articles
        """
        if hours is None:
            hours = self.recent_hours

        collection = await self._get_collection()
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        cursor = collection.find(
            {
                "published_at": {"$gte": cutoff_time},
                "language": "en",  # Only English articles for now
            }
        ).sort(
            "published_at", -1
        )  # Newest first

        articles = []
        async for doc in cursor:
            try:
                articles.append(ArticleInDB(**doc))
            except Exception as e:
                logger.warning(f"Failed to parse article {doc.get('_id')}: {e}")
                continue

        return articles

    def _calculate_article_relevance(self, article: ArticleInDB) -> float:
        """
        Calculate a relevance score for an article based on its content.

        Args:
            article: The article to score

        Returns:
            float: Relevance score (0.0 to 1.0)
        """
        if not article.title or not article.content:
            return 0.0

        text = f"{article.title.lower()} {article.content.lower()}"

        # Check for Bitcoin/crypto keywords
        keyword_score = sum(
            1 for keyword in self.bitcoin_keywords if keyword in text
        ) / len(self.bitcoin_keywords)

        # Check for price-related keywords
        price_score = sum(
            1 for keyword in self.price_keywords if keyword in text
        ) / len(self.price_keywords)

        # Consider article recency (exponential decay)
        hours_old = (
            datetime.now(timezone.utc) - article.published_at
        ).total_seconds() / 3600
        recency_score = max(0, 1 - (hours_old / self.recent_hours))

        # Combine scores with weights
        relevance = (
            0.5 * keyword_score  # Bitcoin/crypto relevance
            + 0.3 * price_score  # Price movement relevance
            + 0.2 * recency_score  # Recency
        )

        return min(1.0, max(0.0, relevance))

    async def get_relevant_news(
        self,
        price_change_percent: float,
        max_articles: int = 3,
        min_relevance: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Get relevant news articles for a given price movement.

        Args:
            price_change_percent: The percentage change in price
            max_articles: Maximum number of articles to return
            min_relevance: Minimum relevance score (0.0 to 1.0)

        Returns:
            List[Dict[str, Any]]: List of relevant article summaries
        """
        try:
            # Get recent articles
            articles = await self.get_recent_articles()

            if not articles:
                logger.info("No recent articles found for correlation")
                return []

            # Calculate relevance for each article
            scored_articles = []
            for article in articles:
                try:
                    relevance = self._calculate_article_relevance(article)
                    if relevance >= min_relevance:
                        scored_articles.append(
                            {
                                "title": article.title,
                                "source": article.source_name or "Unknown",
                                "url": article.url,
                                "published_at": article.published_at.isoformat(),
                                "relevance_score": relevance,
                                "snippet": (
                                    (article.description or "")[:200] + "..."
                                    if article.description
                                    else ""
                                ),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Error processing article {article.id}: {e}")
                    continue

            # Sort by relevance (highest first) and take top N
            scored_articles.sort(key=lambda x: x["relevance_score"], reverse=True)

            return scored_articles[:max_articles]

        except Exception as e:
            logger.error(f"Error in get_relevant_news: {e}", exc_info=True)
            return []


# Singleton instance
news_correlator = NewsCorrelator()
