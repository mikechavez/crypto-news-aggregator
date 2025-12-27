"""
Briefing models for the crypto news briefing agent.

These models define the structure for daily briefings, detected patterns,
and manual inputs that feed into the agentic briefing system.
"""

from datetime import datetime, timezone
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict
from ..db.mongodb import PyObjectId


# ============================================================================
# Nested Models
# ============================================================================

class BriefingRecommendation(BaseModel):
    """A recommended narrative/signal for deeper reading."""

    title: str = Field(..., description="Title of the recommended narrative")
    theme: str = Field(..., description="Theme category (e.g., 'regulatory', 'defi')")
    narrative_id: Optional[str] = Field(None, description="Optional link to narrative ObjectId")


class BriefingContent(BaseModel):
    """The content of a briefing."""

    narrative: str = Field(..., description="Full analyst memo in markdown format")
    key_insights: List[str] = Field(default_factory=list, description="Bullet point insights for history")
    entities_mentioned: List[str] = Field(default_factory=list, description="Entities discussed in this briefing")
    detected_patterns: List[str] = Field(default_factory=list, description="Patterns the agent identified")
    recommendations: List[BriefingRecommendation] = Field(
        default_factory=list,
        description="Recommended reading for deeper exploration"
    )


class BriefingMetadata(BaseModel):
    """Metadata about briefing generation."""

    narratives_analyzed: int = Field(0, description="Number of narratives analyzed")
    signals_analyzed: int = Field(0, description="Number of signals analyzed")
    articles_analyzed: int = Field(0, description="Number of articles analyzed")
    generation_time_ms: int = Field(0, description="Time to generate briefing in ms")
    llm_tokens_used: int = Field(0, description="Total LLM tokens used")
    llm_cost: float = Field(0.0, description="Estimated LLM cost in USD")
    self_refine_triggered: bool = Field(False, description="Whether self-refine loop was triggered")
    feedback_received: bool = Field(False, description="Whether admin has provided feedback")


# ============================================================================
# Briefing Models
# ============================================================================

class BriefingBase(BaseModel):
    """Base model for a daily briefing."""

    type: Literal["morning", "evening"] = Field(..., description="Briefing type")
    content: BriefingContent = Field(..., description="Briefing content")
    metadata: BriefingMetadata = Field(default_factory=BriefingMetadata)
    version: str = Field("2.0", description="Briefing format version")


class BriefingCreate(BriefingBase):
    """Model for creating a new briefing."""
    pass


class BriefingInDB(BriefingBase):
    """Model for briefing as stored in MongoDB."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={PyObjectId: str},
    )


class BriefingResponse(BaseModel):
    """API response for a briefing request."""

    briefing: Optional[BriefingInDB] = Field(None, description="The briefing, if available")
    next_briefing_at: str = Field(..., description="ISO timestamp of next scheduled briefing")


# ============================================================================
# Pattern Models
# ============================================================================

class PatternBase(BaseModel):
    """Base model for a detected pattern."""

    pattern_type: Literal["entity_surge", "sentiment_shift", "event_expected", "narrative_emergence"] = Field(
        ..., description="Type of pattern detected"
    )
    description: str = Field(..., description="Human-readable pattern description")
    entities: List[str] = Field(default_factory=list, description="Entities involved in pattern")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    resolution: Optional[str] = Field(None, description="What happened after (filled later)")


class PatternCreate(PatternBase):
    """Model for creating a new pattern."""

    briefing_id: str = Field(..., description="ID of briefing that detected this pattern")


class PatternInDB(PatternBase):
    """Model for pattern as stored in MongoDB."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    briefing_id: PyObjectId = Field(..., description="ID of briefing that detected this")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={PyObjectId: str},
    )


# ============================================================================
# Manual Input Models
# ============================================================================

class ManualInputBase(BaseModel):
    """Base model for a manual input (external source)."""

    source_type: Literal["blog", "tweet", "report", "newsletter", "other"] = Field(
        ..., description="Type of source"
    )
    source_url: Optional[str] = Field(None, description="URL of the source")
    source_author: Optional[str] = Field(None, description="Author name")
    title: str = Field(..., description="Brief title/description")
    content: str = Field(..., description="Key points or full text")
    admin_notes: Optional[str] = Field(None, description="Admin annotation on why it matters")


class ManualInputCreate(ManualInputBase):
    """Model for creating a manual input."""
    pass


class ManualInputInDB(ManualInputBase):
    """Model for manual input as stored in MongoDB."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["pending", "used", "expired"] = Field("pending", description="Usage status")
    used_in_briefing_id: Optional[PyObjectId] = Field(None, description="Briefing that used this")
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),  # Will be set properly on creation
        description="Auto-expire after 7 days if unused"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={PyObjectId: str},
    )


class ManualInputResponse(BaseModel):
    """API response for manual input."""

    id: str
    title: str
    source_type: str
    status: str
    added_at: str
