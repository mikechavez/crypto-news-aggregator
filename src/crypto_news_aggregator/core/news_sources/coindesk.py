"""CoinDesk news source implementation."""
import json
import logging
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
            name="CoinDesk",
            base_url="https://www.coindesk.com",
            api_key=api_key
        )
        self.api_url = f"{self.base_url}/v2/news"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def fetch_articles(self, 
                           since: Optional[datetime] = None,
                           limit: int = 50) -> AsyncGenerator[Dict[str, Any], None]:
        """Fetch articles from CoinDesk.
        
        Args:
            since: Only return articles published after this time
            limit: Maximum number of articles to return
            
        Yields:
            Article data as dictionaries
            
        Raises:
            RateLimitExceededError: If rate limit is exceeded
            APIError: For other API errors
        """
        if since is None:
            since = self._get_default_since()
            
        params = {
            'page': 1,
            'per_page': min(limit, 50),  # Max 50 per page
            'sort': '-published_at',
            'include_aggregations': 'false'
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        try:
            async with self.client as client:
                while True:
                    response = await client.get(self.api_url, params=params)
                    
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', '60'))
                        raise RateLimitExceededError(
                            f"Rate limit exceeded. Try again in {retry_after} seconds.",
                            retry_after=retry_after
                        )
                        
                    if response.status_code != 200:
                        raise APIError(
                            f"API request failed with status {response.status_code}: {response.text}",
                            status_code=response.status_code
                        )
                    
                    data = response.json()
                    
                    # Process articles
                    articles = data.get('data', [])
                    if not articles:
                        break
                        
                    count = 0
                    for article in articles:
                        article_data = self.format_article(article)
                        if article_data['published_at'] > since:
                            count += 1
                            yield article_data
                    
                    # Log the fetch
                    self._log_fetch(count)
                    
                    # Check if we've reached the limit or there are no more pages
                    if len(articles) < params['per_page'] or count >= limit:
                        break
                        
                    # Get next page
                    params['page'] += 1
                    
        except httpx.RequestError as e:
            raise APIError(f"Request failed: {str(e)}")
    
    def format_article(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """Format a raw CoinDesk article into our standard format.
        
        Args:
            raw_article: Raw article data from CoinDesk API
            
        Returns:
            Formatted article data
        """
        # Extract the first image URL if available
        image_url = None
        if raw_article.get('image') and 'original_url' in raw_article['image']:
            image_url = raw_article['image']['original_url']
        
        # Parse the published date
        published_at = datetime.fromisoformat(
            raw_article['published_at'].replace('Z', '+00:00')
        )
        
        # Format the article URL
        article_url = raw_article.get('url', '')
        if article_url and not article_url.startswith(('http://', 'https://')):
            article_url = f"{self.base_url}{article_url}"
        
        return {
            'source': 'coindesk',
            'source_name': 'CoinDesk',
            'article_id': str(raw_article.get('id', '')),
            'title': raw_article.get('title', '').strip(),
            'description': raw_article.get('description', '').strip(),
            'content': raw_article.get('content', '').strip(),
            'url': article_url,
            'image_url': image_url,
            'published_at': published_at,
            'author': raw_article.get('author', {}).get('name', '').strip(),
            'categories': [cat['name'] for cat in raw_article.get('categories', [])],
            'tags': [tag['slug'] for tag in raw_article.get('tags', [])],
            'raw_data': raw_article  # Keep original data for reference
        }
