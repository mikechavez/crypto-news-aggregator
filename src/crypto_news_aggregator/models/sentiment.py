"""Sentiment-related Pydantic models."""
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


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
