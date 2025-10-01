from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Float,
    JSON,
    Boolean,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Import the Base class
from .base import Base


class Source(Base):
    __tablename__ = "sources"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    url = Column(String, unique=True)
    type = Column(String)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    articles = relationship("Article", back_populates="source")


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("sources.id"))
    title = Column(String)
    description = Column(String)
    author = Column(String)
    content = Column(String)
    url_to_image = Column(String)
    url = Column(String, unique=True)
    published_at = Column(DateTime(timezone=True))
    sentiment_score = Column(Float)
    keywords = Column(JSON)
    additional_data = Column(JSON)
    raw_data = Column(JSON)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    source = relationship("Source", back_populates="articles")
    sentiments = relationship("Sentiment", back_populates="article")


class Sentiment(Base):
    __tablename__ = "sentiments"
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    score = Column(Float)
    magnitude = Column(Float)
    label = Column(String)
    subjectivity = Column(Float)
    raw_data = Column(JSON)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    article = relationship("Article", back_populates="sentiments")


class Trend(Base):
    __tablename__ = "trends"
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    frequency = Column(Integer)
    sentiment_score = Column(Float)
    time_window = Column(String)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class User(Base):
    """User model for database storage."""

    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class Alert(Base):
    """Price alert model for tracking user price alerts."""

    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    symbol = Column(String, default="BTC", nullable=False, index=True)
    price_target = Column(Float, nullable=True)  # Can be null if using percentage
    threshold_percentage = Column(Float, nullable=True)  # e.g., 5.0 for 5%
    direction = Column(String, nullable=False)  # 'above', 'below', or 'both'
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="alerts")

    def __repr__(self):
        return f"<Alert(id={self.id}, user_id={self.user_id}, symbol='{self.symbol}')>"
