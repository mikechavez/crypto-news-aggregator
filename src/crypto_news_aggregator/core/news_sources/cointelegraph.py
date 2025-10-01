"""CoinTelegraph news source implementation."""

import asyncio
import json
import logging
import random
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator

import httpx
from bs4 import BeautifulSoup

from .base import NewsSource, NewsSourceError, RateLimitExceededError, APIError

logger = logging.getLogger(__name__)


class CoinTelegraphSource(NewsSource):
    """News source for CoinTelegraph's cryptocurrency news."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the CoinTelegraph source.

        Args:
            api_key: Optional API key for CoinTelegraph's API (not required for public endpoints)
        """
        super().__init__(
            name="CoinTelegraph",
            base_url="https://api.cointelegraph.com",
            api_key=api_key,
        )
        self.api_url = f"{self.base_url}/v1/news"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def fetch_articles(
        self,
        since: Optional[datetime] = None,
        limit: int = 50,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Fetch articles from CoinTelegraph with retry logic and rate limiting.

        Args:
            since: Only fetch articles published after this datetime.
            limit: Maximum number of articles to fetch.
            max_retries: Maximum number of retry attempts for failed requests.
            initial_backoff: Initial backoff time in seconds (will be doubled after each retry).

        Yields:
            Dict containing article data.

        Raises:
            RateLimitExceededError: If rate limit is exceeded.
            APIError: For other API-related errors.
        """
        params = {
            "limit": min(limit, 100),  # API has a max of 100 per page
            "sort": "published_at",
            "order": "desc",
        }

        if since:
            params["published_after"] = int(since.timestamp())

        # Use a separate client if provided, otherwise use the instance client
        client = self.client
        manage_client = False

        if client is None or client.is_closed:
            client = httpx.AsyncClient(timeout=30.0)
            manage_client = True

        try:
            retries = 0
            backoff = initial_backoff

            while retries <= max_retries:
                try:
                    response = await client.get(self.api_url, params=params)

                    if response.status_code == 429:  # Rate limited
                        retry_after = int(response.headers.get("Retry-After", backoff))
                        logger.warning(
                            f"Rate limited. Retrying after {retry_after} seconds..."
                        )
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()

                    data = response.json()

                    if not data.get("data"):
                        logger.warning("No articles found in response")
                        return

                    for article_data in data["data"]:
                        try:
                            yield self.format_article(article_data)
                        except Exception as e:
                            logger.error(
                                f"Error formatting article: {str(e)}", exc_info=True
                            )
                            continue

                    # Check if we need to paginate
                    if "pagination" in data and "next_url" in data["pagination"]:
                        self.api_url = data["pagination"]["next_url"]
                        if limit > 0:
                            limit -= len(data["data"])
                            if limit <= 0:
                                break
                    else:
                        break

                    # Reset retry counter after successful request
                    retries = 0
                    backoff = initial_backoff

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:  # Rate limited
                        retry_after = int(
                            e.response.headers.get("Retry-After", backoff)
                        )
                        logger.warning(
                            f"Rate limited. Retrying after {retry_after} seconds..."
                        )
                        await asyncio.sleep(retry_after)
                        retries += 1
                        continue
                    elif 500 <= e.response.status_code < 600:  # Server error
                        retries += 1
                        if retries > max_retries:
                            raise APIError(
                                f"Max retries ({max_retries}) exceeded for server error: {str(e)}",
                                status_code=e.response.status_code,
                            )
                        backoff = min(backoff * 2, 300)  # Cap at 5 minutes
                        jitter = backoff * 0.1  # Add ±10% jitter
                        sleep_time = backoff + (random.random() * 2 - 1) * jitter
                        logger.warning(
                            f"Server error {e.response.status_code} (attempt {retries}/{max_retries}). Retrying in {sleep_time:.1f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        continue
                    # For other HTTP errors, raise immediately
                    raise APIError(
                        f"API request failed: {str(e)}",
                        status_code=e.response.status_code,
                    )
                except (httpx.RequestError, json.JSONDecodeError) as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded. Giving up."
                        )
                        raise

                    # Exponential backoff with jitter
                    backoff = min(backoff * 2, 300)  # Cap at 5 minutes
                    jitter = backoff * 0.1  # Add ±10% jitter
                    sleep_time = backoff + (random.random() * 2 - 1) * jitter
                    logger.warning(
                        f"Request failed (attempt {retries}/{max_retries}). Retrying in {sleep_time:.1f}s..."
                    )
                    await asyncio.sleep(sleep_time)
        finally:
            # Only close the client if we created it
            if manage_client and client is not None:
                await client.aclose()

    def _sanitize_html(self, text: str) -> str:
        """Remove HTML tags, convert HTML entities, and normalize whitespace from text.

        Args:
            text: The HTML text to sanitize

        Returns:
            Plain text with HTML tags removed, entities converted, and whitespace normalized
        """
        if not text:
            return ""

        # Convert HTML entities first (e.g., &amp; -> &, &lt; -> <, etc.)
        from html import unescape

        text = unescape(text)

        # Remove any remaining HTML tags
        import re

        text = re.sub(r"<[^>]+>", " ", text)

        # Normalize whitespace and strip
        text = " ".join(text.split())
        return text.strip()

    def _extract_cryptocurrencies(self, text: str) -> List[str]:
        """Extract cryptocurrency mentions from text."""
        if not text:
            return []

        text_lower = text.lower()
        found = set()

        # Look for cryptocurrency names (case insensitive)
        crypto_terms = [
            "bitcoin",
            "ethereum",
            "ripple",
            "litecoin",
            "cardano",
            "polkadot",
            "solana",
            "dogecoin",
            "shiba inu",
            "avalanche",
            "chainlink",
            "bitcoin cash",
            "uniswap",
            "cosmos",
            "algorand",
            "vechain",
            "filecoin",
            "tezos",
            "monero",
            "stellar",
        ]

        for term in crypto_terms:
            # Use word boundaries to avoid partial matches
            if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
                found.add(term)

        # Also look for ticker symbols (e.g., BTC, ETH)
        ticker_map = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "xrp": "ripple",
            "ltc": "litecoin",
            "ada": "cardano",
            "dot": "polkadot",
            "sol": "solana",
            "doge": "dogecoin",
            "shib": "shiba inu",
            "avax": "avalanche",
            "link": "chainlink",
            "bch": "bitcoin cash",
            "uni": "uniswap",
            "atom": "cosmos",
            "algo": "algorand",
            "vet": "vechain",
            "fil": "filecoin",
            "xtz": "tezos",
            "xmr": "monero",
            "xlm": "stellar",
        }

        for ticker, name in ticker_map.items():
            # Match ticker as whole word to avoid false positives
            if re.search(r"\b" + re.escape(ticker) + r"\b", text_lower, re.IGNORECASE):
                found.add(name)

        return sorted(list(found))

    def format_article(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """Format a raw CoinTelegraph article into our standard format.

        Args:
            raw_article: Raw article data from CoinTelegraph API

        Returns:
            Formatted article data

        Raises:
            ValueError: If required fields are missing or malformed
        """
        try:
            # Extract and clean basic fields
            article_id = str(raw_article.get("id", ""))
            if not article_id:
                raise ValueError("Article ID is missing")

            # Parse the published date
            try:
                published_at = datetime.fromtimestamp(
                    raw_article.get("published_at", 0), tz=timezone.utc
                )
                # Convert to ISO format string for JSON serialization
                published_at_iso = published_at.isoformat()
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid or missing publication date: {str(e)}")
                published_at = datetime.now(timezone.utc)
                published_at_iso = published_at.isoformat()

            # Format the article URL
            article_url = raw_article.get("url", "")
            if article_url and not article_url.startswith(("http://", "https://")):
                article_url = f"https://cointelegraph.com{article_url}"

            # Extract and clean content
            title = self._sanitize_html(raw_article.get("title", ""))
            description = self._sanitize_html(raw_article.get("lead", ""))

            # Extract categories and tags first
            categories = []
            if raw_article.get("category"):
                categories.append(
                    self._sanitize_html(raw_article["category"].get("name", ""))
                )

            tags = [
                self._sanitize_html(tag.get("name", ""))
                for tag in raw_article.get("tags", [])
                if tag.get("name")
            ]

            # Combine all text for entity extraction, including categories and tags
            category_text = " ".join(categories) if categories else ""
            tags_text = " ".join(tags) if tags else ""
            full_text = f"{title} {description} {category_text} {tags_text}"

            # Extract the first image URL if available
            image_url = None
            if raw_article.get("cover_image"):
                image_url = raw_article["cover_image"]

            # Extract author information
            author_info = raw_article.get("author", {})
            author_name = self._sanitize_html(author_info.get("name", ""))

            # Extract cryptocurrencies mentioned in the article
            cryptocurrencies = self._extract_cryptocurrencies(full_text)

            # Build the formatted article
            return {
                "source": "cointelegraph",
                "source_name": "CoinTelegraph",
                "article_id": article_id,
                "title": title,
                "description": description,
                "content": description,  # CoinTelegraph doesn't provide full content in the list view
                "url": article_url,
                "canonical_url": article_url,
                "image_url": image_url,
                "published_at": published_at_iso,
                "author": author_name,
                "categories": categories,
                "tags": tags,
                "cryptocurrencies": cryptocurrencies,
                "word_count": len(description.split()),
                "metadata": {
                    "source_id": raw_article.get("id"),
                    "language": raw_article.get("language", "en"),
                    "is_opinion": raw_article.get("is_opinion", False),
                },
                "raw_data": raw_article,  # Keep original data for reference
            }

        except Exception as e:
            logger.error(f"Error formatting article: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to format article: {str(e)}")
