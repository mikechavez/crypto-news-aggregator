from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

# Import the Base class
from .base import Base

# This ensures we only define the tables once
_tables_defined = False

def define_tables():
    global _tables_defined
    if _tables_defined:
        return
        
    _tables_defined = True
    
    # Table definitions will be added here by the following code

# Call define_tables before defining the first model
define_tables()

class Source(Base):
    __tablename__ = "sources"
    __table_args__ = {'extend_existing': True}

    id = Column(String, primary_key=True, index=True)  # Using String to match NewsAPI source IDs
    name = Column(String, unique=True, index=True)
    url = Column(String, unique=True)
    type = Column(String)  # news, twitter, polymarket
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    articles = relationship("Article", back_populates="source")

class Article(Base):
    __tablename__ = "articles"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("sources.id"))
    title = Column(String)
    description = Column(String)  # Short summary/description of the article
    author = Column(String)  # Author of the article
    content = Column(String)
    url_to_image = Column(String)  # URL to the article's main image
    url = Column(String, unique=True)
    published_at = Column(DateTime)
    sentiment_score = Column(Float)
    keywords = Column(JSON)
    additional_data = Column(JSON)
    raw_data = Column(JSON)  # Store complete raw article data from the API  # For additional source-specific data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source = relationship("Source", back_populates="articles")
    sentiments = relationship("Sentiment", back_populates="article")

class Sentiment(Base):
    __tablename__ = "sentiments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"))
    score = Column(Float)
    magnitude = Column(Float)
    label = Column(String)  # Positive, Negative, or Neutral
    subjectivity = Column(Float)  # 0.0 to 1.0
    raw_data = Column(JSON)  # Store complete sentiment analysis data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    article = relationship("Article", back_populates="sentiments")

class Trend(Base):
    __tablename__ = "trends"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    frequency = Column(Integer)
    sentiment_score = Column(Float)
    time_window = Column(String)  # e.g., "1h", "24h", "7d"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
