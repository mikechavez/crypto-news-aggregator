"""Client for interacting with the self-hosted realtime-newsapi."""
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class RealtimeNewsClient:
    """Client for the self-hosted realtime-newsapi service."""
    
    def __init__(self, base_url: str = "http://localhost:3000"):
        """Initialize the client with the base URL of the realtime-newsapi service."""
        self.base_url = base_url.rstrip('/') + '/api/v1'
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to the realtime-newsapi service."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Request to {url} failed: {str(e)}")
            raise
    
    async def get_everything(
        self,
        q: Optional[str] = None,
        sources: Optional[str] = None,
        from_param: Optional[str] = None,
        to: Optional[str] = None,
        language: str = 'en',
        sort_by: str = 'publishedAt',
        page_size: int = 100,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Search for articles matching the specified criteria.
        
        This method is designed to be compatible with the NewsAPI interface.
        """
        params = {
            'q': q,
            'sources': sources,
            'from': from_param,
            'to': to,
            'language': language,
            'sortBy': sort_by,
            'pageSize': page_size,
            'page': page
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        # Map to realtime-newsapi parameters
        mapped_params = {
            'query': params.get('q'),
            'source': params.get('sources'),
            'from_date': params.get('from'),
            'to_date': params.get('to'),
            'language': params.get('language', 'en'),
            'sort_by': params.get('sortBy', 'publishedAt'),
            'limit': params.get('pageSize', 100),
            'offset': (params.get('page', 1) - 1) * params.get('pageSize', 100)
        }
        
        # Remove None values
        mapped_params = {k: v for k, v in mapped_params.items() if v is not None}
        
        response = await self._request('GET', '/articles', params=mapped_params)
        
        # Transform response to match NewsAPI format
        return {
            'status': 'ok',
            'totalResults': len(response),
            'articles': [{
                'source': {'id': article.get('source', {}), 'name': article.get('source', 'Unknown')},
                'author': article.get('author'),
                'title': article.get('title', ''),
                'description': article.get('description'),
                'url': article.get('url', ''),
                'urlToImage': article.get('image_url'),
                'publishedAt': article.get('published_at', ''),
                'content': article.get('content')
            } for article in response]
        }
    
    async def get_sources(
        self,
        category: Optional[str] = None,
        language: str = 'en',
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get available news sources.
        
        This method is designed to be compatible with the NewsAPI interface.
        """
        params = {
            'category': category,
            'language': language,
            'country': country
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        response = await self._request('GET', '/sources', params=params)
        
        # Transform response to match NewsAPI format
        return {
            'status': 'ok',
            'sources': [{
                'id': source.get('id', ''),
                'name': source.get('name', ''),
                'description': source.get('description'),
                'url': source.get('url', ''),
                'category': source.get('category'),
                'language': source.get('language', 'en'),
                'country': source.get('country')
            } for source in response]
        }
    
    async def health_check(self) -> bool:
        """Check if the realtime-newsapi service is healthy."""
        try:
            response = await self._request('GET', '/health')
            return response.get('status') == 'ok'
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
