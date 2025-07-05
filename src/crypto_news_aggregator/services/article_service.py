"""
Article service for handling article-related operations including deduplication.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import hashlib
import re
from unidecode import unidecode
from bson import ObjectId

from ..db.mongodb_models import (
    ArticleInDB,
    ArticleCreate,
    ArticleUpdate,
    SentimentAnalysis,
    SentimentLabel,
    PyObjectId
)
from ..db.mongodb import mongo_manager, COLLECTION_ARTICLES
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ArticleService:
    """Service for handling article operations."""
    
    def __init__(self):
        self.collection_name = COLLECTION_ARTICLES
    
    async def _get_collection(self) -> Any:
        """Get the MongoDB collection for articles."""
        if not hasattr(self, '_collection'):
            # Get the collection and store it
            self._collection = await mongo_manager.get_async_collection("articles")
        return self._collection
    
    async def _generate_fingerprint(self, title: str, content: str) -> str:
        """
        Generate a fingerprint for an article to help with deduplication.
        
        Args:
            title: Article title
            content: Article content
            
        Returns:
            str: A fingerprint string
        """
        # Normalize text: lowercase, remove extra whitespace, and unidecode
        def normalize_text(text: str) -> str:
            if not text:
                return ""
            # Remove URLs, special chars, and extra whitespace
            text = re.sub(r'http\S+', '', text)
            text = re.sub(r'[^\w\s]', '', text)
            text = ' '.join(text.split())
            return unidecode(text.lower())
        
        # Use first 100 chars of title and first 200 chars of content
        normalized = normalize_text(title)[:100] + "\n" + normalize_text(content)[:200]
        
        # Create a hash of the normalized text
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    async def _is_duplicate(self, title: str, content: str, source_id: str, 
                          published_at: datetime) -> Tuple[bool, Optional[ObjectId]]:
        """
        Check if an article is an exact duplicate of an existing one.
        
        Only considers articles with identical fingerprints as duplicates.
        Different articles about the same topic will not be considered duplicates.
        
        Args:
            title: Article title
            content: Article content
            source_id: Source ID (not used in comparison, kept for interface compatibility)
            published_at: Publication timestamp (not used in comparison, kept for interface compatibility)
            
        Returns:
            Tuple of (is_duplicate, original_article_id)
        """
        # Generate fingerprint for the article
        fingerprint = await self._generate_fingerprint(title, content)
        
        # Look for exact matches by fingerprint only
        collection = await self._get_collection()
        existing = await collection.find_one({
            "fingerprint": fingerprint
        })
        
        if existing:
            logger.debug(f"Found duplicate article with fingerprint {fingerprint}")
            return True, existing["_id"]
            
        return False, None
    
    async def create_article(self, article_data: Dict[str, Any]) -> Optional[ArticleInDB]:
        """
        Create a new article with deduplication.
        
        Args:
            article_data: Article data including title, content, source, etc.
            
        Returns:
            ArticleInDB if created, None if it was a duplicate
        """
        # Check for duplicates
        is_duplicate, original_id = await self._is_duplicate(
            title=article_data.get("title", ""),
            content=article_data.get("content", ""),
            source_id=article_data.get("source", {}).get("id", ""),
            published_at=article_data.get("published_at", datetime.now(timezone.utc))
        )
        
        if is_duplicate:
            logger.info(f"Duplicate article detected. Original ID: {original_id}")
            # Update the original article's metadata if needed
            await self._update_duplicate_metadata(original_id, article_data)
            return None
        
        # Generate fingerprint for the article
        fingerprint = await self._generate_fingerprint(
            article_data.get("title", ""),
            article_data.get("content", "")
        )
        
        # Add fingerprint and timestamps
        article_data["fingerprint"] = fingerprint
        article_data["created_at"] = datetime.now(timezone.utc)
        article_data["updated_at"] = datetime.now(timezone.utc)
        
        # Create the article in MongoDB
        collection = await self._get_collection()
        result = await collection.insert_one(article_data)
        
        if result.inserted_id:
            # Return the created article
            created = await collection.find_one({"_id": result.inserted_id})
            return ArticleInDB(**created)
            
        return None
    
    async def _update_duplicate_metadata(self, article_id: ObjectId, new_data: Dict[str, Any]) -> None:
        """
        Update metadata for a duplicate article.
        
        Args:
            article_id: ID of the original article
            new_data: New article data that might contain updates
        """
        update_fields = {}
            
        # Update the updated_at timestamp
        update_fields["updated_at"] = datetime.now(timezone.utc)
        
        # If the new article has a higher quality image, update it
        if new_data.get("url_to_image") and not new_data["url_to_image"].endswith("placeholder.jpg"):
            update_fields["url_to_image"] = new_data["url_to_image"]
            
        # If the new article has more complete content, update it
        if new_data.get("content") and len(new_data["content"]) > 100:  # Arbitrary threshold
            update_fields["content"] = new_data["content"]
        
        # Only perform the update if we have fields to update
        if update_fields:
            collection = await self._get_collection()
            await collection.update_one(
                {"_id": article_id},
                {"$set": update_fields}
            )
    
    async def get_article(self, article_id: str) -> Optional[ArticleInDB]:
        """Get an article by ID."""
        try:
            collection = await self._get_collection()
            article = await collection.find_one({"_id": ObjectId(article_id)})
            return ArticleInDB(**article) if article else None
        except Exception as e:
            logger.error(f"Error getting article {article_id}: {str(e)}")
            return None
    
    async def list_articles(
        self,
        skip: int = 0,
        limit: int = 10,
        source_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        keywords: Optional[List[str]] = None,
        min_sentiment: Optional[float] = None,
        max_sentiment: Optional[float] = None
    ) -> Tuple[List[ArticleInDB], int]:
        """
        List articles with filtering and pagination.
        
        Args:
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            source_id: Filter by source ID
            start_date: Filter by published date (greater than or equal)
            end_date: Filter by published date (less than or equal)
            keywords: Filter by keywords
            min_sentiment: Minimum sentiment score (-1 to 1)
            max_sentiment: Maximum sentiment score (-1 to 1)
            
        Returns:
            Tuple of (list of articles, total count)
        """
        query = {}
        
        # Apply filters
        if source_id:
            query["source.id"] = source_id
            
        if start_date or end_date:
            query["published_at"] = {}
            if start_date:
                query["published_at"]["$gte"] = start_date
            if end_date:
                query["published_at"]["$lte"] = end_date
                
        if keywords:
            query["keywords"] = {"$in": keywords}
            
        if min_sentiment is not None or max_sentiment is not None:
            query["sentiment.score"] = {}
            if min_sentiment is not None:
                query["sentiment.score"]["$gte"] = min_sentiment
            if max_sentiment is not None:
                query["sentiment.score"]["$lte"] = max_sentiment
        
        # Get the MongoDB collection
        collection = await self._get_collection()
        
        # Get total count
        total = await collection.count_documents(query)
        
        # Get paginated results with proper async/await and method chaining
        # First get the cursor by awaiting the find() call
        cursor = await collection.find(query)
        # Then chain the cursor methods (these are synchronous operations)
        cursor = cursor.sort("published_at", -1).skip(skip).limit(limit)
        
        # Execute the query and get results
        articles_data = await cursor.to_list(length=limit)
        articles = [ArticleInDB(**doc) for doc in articles_data]
        
        return articles, total
    
    async def search_articles(
        self,
        query: str,
        skip: int = 0,
        limit: int = 10,
        source_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[List[ArticleInDB], int]:
        """
        Search articles by text.
        
        Args:
            query: Search query string
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            source_id: Filter by source ID
            start_date: Filter by published date (greater than or equal)
            end_date: Filter by published date (less than or equal)
            
        Returns:
            Tuple of (list of articles, total count)
        """
        # Build the text search query
        text_search = {"$text": {"$search": query, "$caseSensitive": False}}
        
        # Build the filter query
        filter_query = {}
        if source_id:
            filter_query["source.id"] = source_id
            
        if start_date or end_date:
            filter_query["published_at"] = {}
            if start_date:
                filter_query["published_at"]["$gte"] = start_date
            if end_date:
                filter_query["published_at"]["$lte"] = end_date
        
        # Combine text search with filters
        query = {"$and": [text_search]}
        if filter_query:
            query["$and"].append(filter_query)
        else:
            query = text_search
        
        collection = await self._get_collection()
        
        # Get total count
        total = await collection.count_documents(query)
        
        # Get search results with text score for sorting
        pipeline = [
            {"$match": query},
            {"$addFields": {"score": {"$meta": "textScore"}}},
            {"$sort": {"score": {"$meta": "textScore"}}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        # Execute aggregation and convert to list
        cursor = await collection.aggregate(pipeline)
        articles_data = await cursor.to_list(length=limit)
        articles = [ArticleInDB(**doc) for doc in articles_data]
        
        return articles, total
    
    async def update_article_sentiment(
        self, 
        article_id: str, 
        sentiment: SentimentAnalysis
    ) -> bool:
        """
        Update the sentiment analysis for an article.
        
        Args:
            article_id: Article ID
            sentiment: Sentiment analysis data
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            collection = await self._get_collection()
            result = await collection.update_one(
                {"_id": ObjectId(article_id)},
                {
                    "$set": {
                        "sentiment": sentiment.model_dump(),
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating article {article_id} sentiment: {str(e)}")
            return False


# Singleton instance
article_service = ArticleService()
