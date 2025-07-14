"""
Article model for storing and processing news articles.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from bson import ObjectId
from ..db.mongodb import PyObjectId

class ArticleBase(BaseModel):
    """Base model for article data."""
    title: str
    content: str
    source_name: str
    url: HttpUrl
    published_at: datetime
    author: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    language: str = "en"
    category: Optional[str] = None
    tags: List[str] = []
    sentiment_score: Optional[float] = None
    entities: List[Dict[str, Any]] = []

class ArticleCreate(ArticleBase):
    """Model for creating a new article."""
    pass

class ArticleInDB(ArticleBase):
    """Model for article data stored in the database."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "title": "Bitcoin Price Surges Past $60,000",
                "content": "Bitcoin has reached a new all-time high...",
                "source_name": "CryptoNews",
                "url": "https://example.com/bitcoin-news",
                "published_at": "2023-04-01T12:00:00Z",
                "author": "John Doe",
                "description": "Bitcoin reaches new all-time high",
                "language": "en",
                "category": "cryptocurrency",
                "tags": ["bitcoin", "price", "crypto"],
                "sentiment_score": 0.85,
                "entities": [
                    {"text": "Bitcoin", "type": "CRYPTOCURRENCY", "relevance": 0.99}
                ]
            }
        }

class Article(ArticleInDB):
    """Public-facing article model (excludes internal fields)."""
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
