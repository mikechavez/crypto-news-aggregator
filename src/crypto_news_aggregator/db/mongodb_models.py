"""
MongoDB models for the Crypto News Aggregator.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from bson import ObjectId
from enum import Enum, IntEnum

class PyObjectId(ObjectId):
    """Custom type for MongoDB ObjectId that works with Pydantic v2."""
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        
        def validate_object_id(value: str) -> ObjectId:
            if not ObjectId.is_valid(value):
                raise ValueError("Invalid ObjectId")
            return ObjectId(value)
            
        return core_schema.no_info_plain_validator_function(
            function=validate_object_id,
            serialization=core_schema.to_string_ser_schema(),
        )
        
    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema, handler):
        return handler(core_schema.str_schema())


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class SentimentAnalysis(BaseModel):
    """Sentiment analysis result for an article."""
    score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score between -1 (negative) and 1 (positive)")
    magnitude: float = Field(..., ge=0, description="Magnitude of the sentiment")
    label: SentimentLabel = Field(..., description="Sentiment label")
    subjectivity: float = Field(..., ge=0, le=1.0, description="Subjectivity score between 0 (objective) and 1 (subjective)")
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ArticleSource(BaseModel):
    """Source information for an article."""
    id: Optional[str] = None
    name: str
    url: Optional[HttpUrl] = None
    type: Optional[str] = None


class ArticleBase(BaseModel):
    """Base model for article data."""
    title: str
    description: Optional[str] = None
    content: str
    url: HttpUrl
    url_to_image: Optional[HttpUrl] = None
    author: Optional[str] = None
    published_at: datetime
    source: ArticleSource
    language: str = "en"
    category: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    entities: Dict[str, List[str]] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ArticleCreate(ArticleBase):
    """Model for creating a new article."""
    pass


class ArticleUpdate(BaseModel):
    """Model for updating an existing article."""
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    url_to_image: Optional[HttpUrl] = None
    keywords: Optional[List[str]] = None
    entities: Optional[Dict[str, List[str]]] = None
    metadata: Optional[Dict[str, Any]] = None


class ArticleInDB(ArticleBase):
    """Article model as stored in MongoDB."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    sentiment: Optional[SentimentAnalysis] = None
    is_duplicate: bool = False
    duplicate_of: Optional[PyObjectId] = None
    processed: bool = False
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "example": {
                "title": "Bitcoin Reaches New All-Time High",
                "description": "Bitcoin price surges past $100,000",
                "content": "Full article content...",
                "url": "https://example.com/bitcoin-news",
                "source": {"name": "Crypto News"},
                "published_at": "2023-01-01T00:00:00Z"
            }
        }
    }


class ArticleResponse(ArticleInDB):
    """Article model for API responses."""
    id: str = Field(..., alias="_id")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class AlertStatus(str, Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    DISABLED = "disabled"


# Indexes to be created on MongoDB collections
PRICE_HISTORY_INDEXES = [
    # Compound index for querying price history by cryptocurrency and timestamp
    [
        ("cryptocurrency", 1),  # Group by cryptocurrency
        ("timestamp", -1)       # Sort by timestamp descending (newest first)
    ],
    # TTL index to automatically remove old price data (keep 30 days)
    [
        ("timestamp", 1),
        {
            "expireAfterSeconds": 2592000  # 30 days in seconds
        }
    ]
]

ALERT_INDEXES = [
    # Index for fast lookups by user_id and active status
    {
        "keys": [("user_id", 1), ("is_active", 1)],
        "name": "user_active_alerts",
        "background": True
    },
    # Index for finding active alerts for a specific cryptocurrency
    {
        "keys": [("crypto_id", 1), ("is_active", 1), ("last_triggered", -1)],
        "name": "crypto_active_alerts",
        "background": True
    },
    # TTL index for automatically expiring old alerts after 90 days
    {
        "keys": [("created_at", 1)],
        "name": "alert_expiration",
        "expireAfterSeconds": 90 * 24 * 60 * 60  # 90 days in seconds
    }
]

class EmailEventType(str, Enum):
    """Types of email events that can be tracked."""
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    UNSUBSCRIBED = "unsubscribed"


class EmailEvent(BaseModel):
    """Model for tracking individual email events."""
    event_type: EmailEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[Dict[str, Any]] = None


class EmailTracking(BaseModel):
    """Model for tracking email delivery and interactions."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    message_id: str  # Unique identifier for the email
    user_id: PyObjectId  # Reference to the user
    recipient_email: str
    template_name: str
    subject: str
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    events: List[EmailEvent] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        """Pydantic config."""
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# Email tracking indexes
EMAIL_TRACKING_INDEXES = [
    # Index for message lookups
    {
        "keys": [("message_id", 1)],
        "name": "message_id_unique",
        "unique": True
    },
    # Index for user's email history
    {
        "keys": [("user_id", 1), ("sent_at", -1)],
        "name": "user_email_history"
    },
    # Index for tracking events by type and time
    {
        "keys": [("events.event_type", 1), ("events.timestamp", -1)],
        "name": "event_type_tracking"
    },
    # TTL index to automatically remove old tracking data after 1 year
    {
        "keys": [("sent_at", 1)],
        "name": "email_tracking_ttl",
        "expireAfterSeconds": 31536000  # 1 year in seconds
    }
]


ARTICLE_INDEXES = [
    {
        "keys": [("url", 1)],
        "name": "url_unique",
        "unique": True
    },
    {
        "keys": [("title", "text"), ("content", "text"), ("description", "text")],
        "name": "full_text_search",
        "default_language": "english",
        "weights": {"title": 10, "description": 5, "content": 1}
    },
    {
        "keys": [("published_at", -1)],
        "name": "published_at_desc"
    },
    {
        "keys": [("source.id", 1)],
        "name": "source_id"
    },
    {
        "keys": [("sentiment.score", 1)],
        "name": "sentiment_score"
    },
    {
        "keys": [("keywords", 1)],
        "name": "keywords_idx"
    },
    {
        "keys": [("is_duplicate", 1)],
        "name": "is_duplicate"
    },
    {
        "keys": [("processed", 1)],
        "name": "processed_flag"
    }
]
