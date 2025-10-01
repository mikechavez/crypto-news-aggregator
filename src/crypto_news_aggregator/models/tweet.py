"""
Tweet model for storing and processing Twitter data, designed for MongoDB.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from ..db.mongodb import PyObjectId


class TweetMetrics(BaseModel):
    """Public metrics for a tweet."""

    impressions: int = 0
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    quotes: int = 0


class TweetAuthor(BaseModel):
    """Author of a tweet."""

    id: str
    name: str
    username: str


class TweetBase(BaseModel):
    """Base model for tweet data."""

    tweet_id: str = Field(..., unique=True)
    text: str
    author: TweetAuthor
    url: HttpUrl
    lang: str = "en"
    metrics: TweetMetrics
    keywords: List[str] = []
    relevance_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    raw_data: Dict[str, Any]  # To store the raw tweet payload
    tweet_created_at: datetime  # Timestamp from Twitter


class TweetCreate(TweetBase):
    """Model for creating a new tweet document."""

    pass


class TweetUpdate(BaseModel):
    """Model for updating an existing tweet document."""

    text: Optional[str] = None
    relevance_score: Optional[float] = None
    metrics: Optional[TweetMetrics] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))


class TweetInDB(TweetBase):
    """Model for tweet data as stored in MongoDB."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.UTC))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={PyObjectId: str},
        json_schema_extra={
            "example": {
                "tweet_id": "1234567890",
                "text": "Bitcoin to the moon! $BTC",
                "author": {
                    "id": "123",
                    "name": "Crypto King",
                    "username": "cryptoking",
                },
                "url": "https://twitter.com/cryptoking/status/1234567890",
                "lang": "en",
                "metrics": {
                    "impressions": 10000,
                    "likes": 500,
                    "retweets": 100,
                    "replies": 20,
                    "quotes": 5,
                },
                "keywords": ["$BTC"],
                "relevance_score": 0.95,
                "raw_data": {},
                "tweet_created_at": "2025-09-21T12:00:00Z",
            }
        },
    )
