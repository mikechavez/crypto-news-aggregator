"""CoinDesk news source implementation."""

import asyncio
import json
import logging
import random
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator

import httpx

from .base import NewsSource, NewsSourceError, RateLimitExceededError, APIError

logger = logging.getLogger(__name__)


class CoinDeskSource(NewsSource):
    """News source for CoinDesk's cryptocurrency news."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the CoinDesk source.

        Args:
            api_key: Optional API key for CoinDesk's API (not required for public endpoints)
        """
        super().__init__(
            name="CoinDesk", base_url="https://www.coindesk.com", api_key=api_key
        )
        self.api_url = f"{self.base_url}/v2/news"
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
        request_timeout: float = 30.0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Fetch articles from CoinDesk with retry logic, rate limiting, and pagination.

        This method handles the complete article fetching process including error handling,
        rate limiting, and pagination. It respects the API's rate limits and implements
        exponential backoff with jitter for retries.

        Args:
            since: Only fetch articles published after this datetime. If None, fetches all available articles.
            limit: Maximum number of articles to fetch. Must be between 1 and 1000.
            max_retries: Maximum number of retry attempts for failed requests. Must be >= 0.
            initial_backoff: Initial backoff time in seconds. Will be doubled after each retry.
            request_timeout: Maximum time in seconds to wait for a response from the API.

        Yields:
            Dict containing formatted article data for each article.

        Raises:
            ValueError: If input parameters are invalid.
            httpx.HTTPStatusError: For HTTP errors that can't be retried.
            httpx.RequestError: For request errors that can't be retried.

        Example:
            >>> async with CoinDeskSource() as source:
            ...     async for article in source.fetch_articles(limit=5):
            ...         print(article['title'])
        """
        # Input validation
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            raise ValueError("limit must be an integer between 1 and 1000")

        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")

        if not isinstance(initial_backoff, (int, float)) or initial_backoff <= 0:
            raise ValueError("initial_backoff must be a positive number")

        if not isinstance(request_timeout, (int, float)) or request_timeout <= 0:
            raise ValueError("request_timeout must be a positive number")

        page = 1
        per_page = min(limit, 50)  # API max is 50 per page
        count = 0

        # Track rate limit state
        rate_limit_remaining = float("inf")
        rate_limit_reset = 0

        # Determine if we should manage the client lifecycle
        manage_client = not hasattr(self, "client") or not self.client

        # Use the instance client if it exists, otherwise create a new one
        client = self.client if hasattr(self, "client") and self.client else None

        try:
            if client is None:
                client = httpx.AsyncClient(timeout=request_timeout)

            while count < limit:
                retries = 0
                backoff = initial_backoff

                # Check rate limits before making a request
                if rate_limit_remaining == 0:
                    wait_time = (
                        max(rate_limit_reset - time.time(), 0) + 1
                    )  # Add 1s buffer
                    if wait_time > 0:
                        logger.info(
                            f"Rate limit reached. Waiting {wait_time:.1f}s before next request..."
                        )
                        await asyncio.sleep(wait_time)

                while retries <= max_retries:
                    try:
                        # Build the URL with query parameters
                        params = {
                            "page": page,
                            "per_page": per_page,
                            "sort": "-published_at",  # Newest first
                            "include_aggregations": "false",
                        }

                        # Add date filter if provided
                        if since is not None:
                            params["published_after"] = since.isoformat()

                        # Make the request with timeout
                        start_time = time.time()
                        response = await client.get(
                            f"{self.base_url}/v2/news",
                            params=params,
                            headers={
                                "Accept": "application/json",
                                "User-Agent": "CryptoNewsAggregator/1.0 (https://github.com/yourusername/crypto-news-aggregator)",
                            },
                            timeout=request_timeout,
                        )

                        # Update rate limit info from headers if available
                        rate_limit_remaining_str = response.headers.get(
                            "X-RateLimit-Remaining"
                        )
                        rate_limit_remaining = (
                            int(rate_limit_remaining_str)
                            if rate_limit_remaining_str
                            and rate_limit_remaining_str.lower() != "inf"
                            else float("inf")
                        )
                        rate_limit_reset = int(
                            response.headers.get("X-RateLimit-Reset", 0)
                        )

                        response.raise_for_status()

                        # Log successful request
                        request_time = time.time() - start_time
                        logger.debug(f"Fetched page {page} in {request_time:.2f}s")

                        # Process the response
                        try:
                            data = response.json()
                            articles = data.get("data", [])
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Could not decode JSON from CoinDesk. The service may be blocking requests. "
                                f"Status: {response.status_code}. Response: {response.text[:200]}..."
                            )
                            # CoinDesk is returning HTML instead of JSON (likely blocking).
                            # Stop fetching from this source and return what we have.
                            logger.info(f"Stopping fetch from CoinDesk due to HTML response (blocking detected)")
                            return  # Exit both retry loop AND outer while loop

                        if not articles:
                            logger.info(f"No more articles found at page {page}")
                            return  # No more articles

                        # Process each article
                        articles_processed = 0
                        for article in articles:
                            try:
                                article_data = self.format_article(article)
                                published_at = article_data.get("published_at")

                                # Skip if article is older than 'since' (double check)
                                if since is not None and published_at:
                                    if isinstance(published_at, str):
                                        try:
                                            published_at = datetime.fromisoformat(
                                                published_at.replace("Z", "+00:00")
                                            ).replace(tzinfo=timezone.utc)
                                        except (ValueError, AttributeError) as e:
                                            logger.warning(
                                                f"Invalid published_at format '{published_at}': {e}. "
                                                f"Article ID: {article.get('id', 'unknown')}"
                                            )
                                            continue

                                    if published_at <= since:
                                        logger.debug(
                                            f"Skipping article {article.get('id', 'unknown')} "
                                            f"published at {published_at} (older than {since})"
                                        )
                                        continue

                                count += 1
                                articles_processed += 1
                                yield article_data

                                if count >= limit:
                                    logger.info(f"Reached article limit of {limit}")
                                    return

                            except Exception as e:
                                article_id = article.get("id", "unknown")
                                logger.error(
                                    f"Error processing article {article_id}: {str(e)}",
                                    exc_info=True,
                                )
                                continue

                        logger.debug(
                            f"Processed {articles_processed} articles from page {page}"
                        )

                        # Move to next page if we haven't reached the limit
                        page += 1
                        break  # Success, exit retry loop

                    except httpx.HTTPStatusError as e:
                        status_code = e.response.status_code

                        if status_code == 429:  # Rate limited
                            retry_after = int(
                                e.response.headers.get("Retry-After", backoff)
                            )
                            logger.warning(
                                f"Rate limited. Headers: {dict(e.response.headers)}. "
                                f"Retrying after {retry_after} seconds..."
                            )
                            await asyncio.sleep(retry_after)
                            continue

                        elif 500 <= status_code < 600:  # Server error
                            logger.error(
                                f"Server error {status_code} on page {page}. "
                                f"Attempt {retries + 1}/{max_retries + 1}"
                            )
                            if retries >= max_retries:
                                logger.error(
                                    f"Max retries ({max_retries}) exceeded. "
                                    f"Last status: {status_code}"
                                )
                                raise
                        else:
                            logger.error(
                                f"HTTP {status_code} error: {e.response.text[:200]}..."
                            )
                            raise

                    except (httpx.RequestError, json.JSONDecodeError) as e:
                        logger.error(f"Request failed: {str(e)}")
                        if retries >= max_retries:
                            logger.error(
                                f"Max retries ({max_retries}) exceeded. Last error: {e}"
                            )
                            raise

                    # If we get here, the request failed and we should retry
                    retries += 1

                    # Calculate backoff with jitter
                    backoff = min(backoff * 2, 300)  # Cap at 5 minutes
                    jitter = backoff * 0.1  # Add ±10% jitter
                    sleep_time = backoff + (random.random() * 2 - 1) * jitter

                    logger.warning(
                        f"Request failed (attempt {retries}/{max_retries + 1}). "
                        f"Retrying in {sleep_time:.1f}s..."
                    )
                    await asyncio.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Fatal error in fetch_articles: {str(e)}", exc_info=True)
            raise

        finally:
            # Only close the client if we created it
            if manage_client and client is not None:
                try:
                    await client.aclose()
                except Exception as e:
                    logger.error(f"Error closing HTTP client: {str(e)}")

            logger.info(f"Fetched {count} articles in total")

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

        # Also check categories and tags in the article
        if hasattr(self, "_current_article"):
            for category in self._current_article.get("categories", []):
                if "name" in category:
                    cat_name = category["name"].lower()
                    if cat_name in crypto_terms:
                        found.add(cat_name)

            for tag in self._current_article.get("tags", []):
                if "slug" in tag:
                    tag_slug = tag["slug"].lower()
                    if tag_slug in crypto_terms:
                        found.add(tag_slug)

        return sorted(list(found))

    def format_article(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """Format a raw CoinDesk article into our standard format with enhanced processing.

        This method takes a raw article from the CoinDesk API and transforms it into a
        standardized format with consistent field names and data types. It performs
        validation, sanitization, and enrichment of the article data.

        Args:
            raw_article: Raw article data from CoinDesk API. Must be a dictionary containing
                       at minimum an 'id' and 'published_at' field.

        Returns:
            Dict containing the formatted article with the following structure:
            {
                'source': str,           # Source identifier ('coindesk')
                'source_name': str,      # Human-readable source name
                'article_id': str,       # Unique identifier for the article
                'title': str,            # Article title (HTML sanitized)
                'description': str,      # Article description (HTML sanitized)
                'content': str,          # Full article content (HTML sanitized)
                'url': str,              # Full URL to the article
                'canonical_url': str,    # Canonical URL if different from url
                'image_url': str,        # URL to the main article image
                'published_at': str,     # ISO 8601 formatted datetime string
                'author': str,           # Author name (sanitized)
                'categories': List[str], # List of category names
                'tags': List[str],       # List of tag names
                'cryptocurrencies': List[str],  # Cryptocurrencies mentioned
                'word_count': int,       # Approximate word count
                'metadata': {            # Additional metadata
                    'source_id': str,    # Original source ID
                    'source_created_at': str,  # Original creation time
                    'source_updated_at': str,  # Last update time
                    'language': str,     # Content language code
                    'is_opinion': bool   # Whether this is an opinion piece
                },
                'raw_data': dict         # Original raw article data
            }

        Raises:
            ValueError: If required fields are missing or malformed
            TypeError: If raw_article is not a dictionary

        Example:
            >>> source = CoinDeskSource()
            >>> article = {
            ...     'id': '123',
            ...     'title': 'Test Title',
            ...     'published_at': '2023-01-01T12:00:00Z',
            ...     'content': 'Test content',
            ...     'url': '/test-article'
            ... }
            >>> formatted = source.format_article(article)
            >>> formatted['title']
            'Test Title'
        """
        if not isinstance(raw_article, dict):
            raise TypeError(
                f"Expected dict for raw_article, got {type(raw_article).__name__}"
            )

        try:
            # Store the raw article for cryptocurrency extraction
            self._current_article = raw_article

            # Validate required fields
            required_fields = ["id", "published_at"]
            missing_fields = [
                field for field in required_fields if field not in raw_article
            ]
            if missing_fields:
                raise ValueError(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )

            # Extract and clean basic fields with validation
            article_id = str(raw_article["id"]).strip()
            if not article_id:
                raise ValueError("Article ID cannot be empty")

            # Parse and validate the published date
            try:
                published_at_str = str(raw_article["published_at"]).strip()
                if not published_at_str:
                    raise ValueError("Published date cannot be empty")

                # Handle both 'Z' and '+00:00' timezone formats
                if published_at_str.endswith("Z"):
                    published_at_str = published_at_str[:-1] + "+00:00"

                published_at = datetime.fromisoformat(published_at_str)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)

                published_at_iso = published_at.isoformat()

            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Invalid publication date '{raw_article['published_at']}': {str(e)}"
                )
                published_at = datetime.now(timezone.utc)
                published_at_iso = published_at.isoformat()

            # Format the article URL with validation
            article_url = str(raw_article.get("url", "")).strip()
            if article_url:
                if not article_url.startswith(("http://", "https://")):
                    article_url = (
                        f"{self.base_url.rstrip('/')}/{article_url.lstrip('/')}"
                    )

            # Extract and clean content with HTML sanitization
            title = self._sanitize_html(str(raw_article.get("title", ""))).strip()
            if not title:
                logger.warning(f"Article {article_id} has empty title")

            description = self._sanitize_html(
                str(raw_article.get("description", ""))
            ).strip()
            content = self._sanitize_html(str(raw_article.get("content", ""))).strip()

            # Combine all text for entity extraction
            full_text = f"{title} {description} {content}"

            # Extract the first image URL if available
            image_url = None
            if (
                isinstance(raw_article.get("image"), dict)
                and "original_url" in raw_article["image"]
            ):
                image_url = str(raw_article["image"]["original_url"]).strip()

            # Extract author information with validation
            author_name = ""
            if (
                isinstance(raw_article.get("author"), dict)
                and "name" in raw_article["author"]
            ):
                author_name = self._sanitize_html(
                    str(raw_article["author"]["name"])
                ).strip()

            # Extract and validate categories
            categories = []
            if isinstance(raw_article.get("categories"), list):
                categories = [
                    self._sanitize_html(str(cat.get("name", ""))).strip()
                    for cat in raw_article["categories"]
                    if isinstance(cat, dict) and cat.get("name")
                ]

            # Extract and validate tags
            tags = []
            if isinstance(raw_article.get("tags"), list):
                tags = [
                    self._sanitize_html(str(tag.get("slug", ""))).strip()
                    for tag in raw_article["tags"]
                    if isinstance(tag, dict) and tag.get("slug")
                ]

            # Extract cryptocurrencies mentioned in the article
            cryptocurrencies = self._extract_cryptocurrencies(full_text)

            # Calculate word count (approximate)
            word_count = len(content.split()) if content else 0

            # Determine if this is an opinion piece
            is_opinion = any(
                t.lower() in {"opinion", "op-ed", "editorial"}
                for t in tags + categories + [title.lower()]
            )

            # Build the formatted article
            formatted = {
                "source": "coindesk",
                "source_name": "CoinDesk",
                "article_id": article_id,
                "title": title,
                "description": description,
                "content": content,
                "url": article_url,
                "canonical_url": article_url,
                "image_url": image_url,
                "published_at": published_at_iso,
                "author": author_name,
                "categories": categories,
                "tags": tags,
                "cryptocurrencies": sorted(
                    list(set(cryptocurrencies))
                ),  # Remove duplicates
                "word_count": word_count,
                "metadata": {
                    "source_id": article_id,
                    "source_created_at": str(raw_article.get("created_at", "")),
                    "source_updated_at": str(raw_article.get("updated_at", "")),
                    "language": str(raw_article.get("language", "en")).lower(),
                    "is_opinion": is_opinion,
                },
                "raw_data": raw_article,  # Keep original data for reference
            }

            return formatted

        except Exception as e:
            error_msg = (
                f"Error formatting article {raw_article.get('id', 'unknown')}: {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg) from e
            raise ValueError(f"Failed to format article: {str(e)}")
