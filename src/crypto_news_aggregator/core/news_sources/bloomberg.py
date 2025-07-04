"""Bloomberg news source implementation."""
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
import httpx
from bs4 import BeautifulSoup

from .base import NewsSource, NewsSourceError, RateLimitExceededError, APIError

logger = logging.getLogger(__name__)

class BloombergSource(NewsSource):
    """News source for Bloomberg market news.
    
    Note: This implementation scrapes Bloomberg's website since their API requires a paid subscription.
    For production use, consider using Bloomberg's official API with proper authentication.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Bloomberg source.
        
        Args:
            api_key: Not currently used, kept for API compatibility
        """
        super().__init__(
            name="Bloomberg",
            base_url="https://www.bloomberg.com",
            api_key=api_key
        )
        self.markets_url = f"{self.base_url}/markets"
        self.client = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            timeout=30.0,
            follow_redirects=True
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def fetch_articles(self, 
                           since: Optional[datetime] = None,
                           limit: int = 20) -> AsyncGenerator[Dict[str, Any], None]:
        """Fetch market news articles from Bloomberg.
        
        Args:
            since: Only return articles published after this time
            limit: Maximum number of articles to return
            
        Yields:
            Article data as dictionaries
            
        Raises:
            RateLimitExceededError: If rate limit is detected
            APIError: For other errors
        """
        if since is None:
            since = self._get_default_since()
            
        try:
            # First, get the main markets page to find article links
            response = await self.client.get(self.markets_url)
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', '60'))
                raise RateLimitExceededError(
                    f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    retry_after=retry_after
                )
                
            if response.status_code != 200:
                raise APIError(
                    f"Failed to fetch Bloomberg markets page: {response.status_code}",
                    status_code=response.status_code
                )
            
            # Parse the HTML to find article links
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find article containers - this selector may need adjustment if Bloomberg changes their HTML
            article_containers = soup.select('article.story-item')
            if not article_containers:
                # Try alternative selectors if the first one doesn't work
                article_containers = soup.select('div[data-component="headline-story"]')
            
            count = 0
            for container in article_containers[:limit]:
                try:
                    # Extract article URL
                    link = container.find('a', href=True)
                    if not link:
                        continue
                        
                    article_url = link['href']
                    if not article_url.startswith(('http://', 'https://')):
                        article_url = f"{self.base_url}{article_url}"
                    
                    # Skip if we've already processed this article
                    # In a real implementation, you'd check against a database here
                    
                    # Fetch the full article
                    article_data = await self._fetch_article(article_url)
                    if article_data and article_data.get('published_at', datetime.min.replace(tzinfo=timezone.utc)) > since:
                        count += 1
                        yield article_data
                        
                except Exception as e:
                    logger.error(f"Error processing article: {e}", exc_info=True)
                    continue
            
            # Log the fetch
            self._log_fetch(count)
            
        except httpx.RequestError as e:
            raise APIError(f"Request failed: {str(e)}")
    
    async def _fetch_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse a single article.
        
        Args:
            url: URL of the article to fetch
            
        Returns:
            Parsed article data or None if there was an error
        """
        try:
            response = await self.client.get(url)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch article {url}: {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract article data - these selectors may need adjustment
            title_elem = soup.select_one('h1.lede-text-v2__hed')
            title = title_elem.get_text().strip() if title_elem else ""
            
            # Extract published date
            time_elem = soup.select_one('time[data-time]')
            published_at = datetime.now(timezone.utc)  # Default to now
            if time_elem and 'datetime' in time_elem.attrs:
                try:
                    published_at = datetime.fromisoformat(
                        time_elem['datetime'].replace('Z', '+00:00')
                    )
                except (ValueError, TypeError):
                    pass
            
            # Extract article content
            content_elems = soup.select('div.body-copy-v2 p')
            content = '\n\n'.join(p.get_text().strip() for p in content_elems)
            
            # Extract author
            author_elem = soup.select_one('a[data-tracking-type="byline"]')
            author = author_elem.get_text().strip() if author_elem else ""
            
            # Extract categories/tags
            categories = []
            tag_elems = soup.select('a[data-tracking-type="topic"]')
            for tag in tag_elems:
                categories.append(tag.get_text().strip())
            
            return {
                'source': 'bloomberg',
                'source_name': 'Bloomberg',
                'article_id': self._extract_article_id(url),
                'title': title,
                'description': content[:200] + '...' if content else "",
                'content': content,
                'url': url,
                'image_url': self._extract_image_url(soup),
                'published_at': published_at,
                'author': author,
                'categories': categories,
                'tags': [],
                'raw_data': {
                    'url': url
                }
            }
            
        except Exception as e:
            logger.error(f"Error fetching article {url}: {e}", exc_info=True)
            return None
    
    def _extract_article_id(self, url: str) -> str:
        """Extract a unique article ID from the URL."""
        # Extract the last part of the URL as the ID
        return url.rstrip('/').split('/')[-1].split('?')[0] or ""
    
    def _extract_image_url(self, soup) -> Optional[str]:
        """Extract the main image URL from the article."""
        # Try to find the main article image
        img = soup.select_one('picture img')
        if img and 'src' in img.attrs:
            return img['src']
        
        # Try OpenGraph image
        og_img = soup.find('meta', property='og:image')
        if og_img and 'content' in og_img.attrs:
            return og_img['content']
            
        return None
    
    def format_article(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """Format a raw article into our standard format.
        
        This method is kept for API compatibility but isn't used in this implementation
        since we already format articles in _fetch_article.
        """
        return raw_article
