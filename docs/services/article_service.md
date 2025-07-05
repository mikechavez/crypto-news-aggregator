# Article Service

The `ArticleService` class provides methods for managing articles in the Crypto News Aggregator application. It handles operations such as creating, retrieving, updating, and searching articles, with built-in deduplication and filtering capabilities.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Overview

The `ArticleService` is responsible for managing article data in the MongoDB database. It provides a high-level interface for common article operations, abstracting away the underlying database implementation details.

## Features

- **Article Management**: Create, retrieve, update, and delete articles
- **Deduplication**: Prevent duplicate articles using content fingerprinting
- **Search & Filtering**: Advanced search with multiple filter criteria
- **Pagination**: Support for large result sets with skip/limit pagination
- **Sentiment Analysis**: Track and update article sentiment scores

## Usage

### Initialization

```python
from src.crypto_news_aggregator.services.article_service import ArticleService

# Create an instance of the service
article_service = ArticleService()
```

### Creating an Article

```python
article_data = {
    "title": "Bitcoin Reaches New All-Time High",
    "content": "Bitcoin has reached a new all-time high of $100,000...",
    "url": "https://example.com/bitcoin-all-time-high",
    "source": {
        "id": "example-news",
        "name": "Example News"
    },
    "published_at": "2023-01-01T12:00:00Z"
}

# Create the article
created_article = await article_service.create_article(article_data)
```

### Retrieving Articles

```python
# Get a single article by ID
article = await article_service.get_article("507f1f77bcf86cd799439011")

# List articles with pagination
articles, total = await article_service.list_articles(
    skip=0,
    limit=10,
    source_id="example-news"
)

# Search articles by text query
search_results, total = await article_service.search_articles(
    query="bitcoin price",
    limit=5
)
```

## API Reference

### `get_article(article_id: str) -> Optional[ArticleInDB]`

Retrieve a single article by its ID.

**Parameters:**
- `article_id` (str): The MongoDB ObjectId of the article

**Returns:**
- `Optional[ArticleInDB]`: The article if found, None otherwise

---

### `create_article(article_data: Dict[str, Any]) -> Optional[ArticleInDB]`

Create a new article with deduplication.

**Parameters:**
- `article_data` (Dict[str, Any]): Article data including title, content, source, etc.

**Returns:**
- `Optional[ArticleInDB]`: The created article if successful, None if it was a duplicate

---

### `list_articles(skip: int = 0, limit: int = 10, **filters) -> Tuple[List[ArticleInDB], int]`

List articles with filtering and pagination.

**Parameters:**
- `skip` (int): Number of documents to skip (for pagination)
- `limit` (int): Maximum number of documents to return
- `source_id` (Optional[str]): Filter by source ID
- `start_date` (Optional[datetime]): Filter by start date
- `end_date` (Optional[datetime]): Filter by end date
- `keywords` (Optional[List[str]]): Filter by keywords
- `min_sentiment` (Optional[float]): Minimum sentiment score (-1 to 1)
- `max_sentiment` (Optional[float]): Maximum sentiment score (-1 to 1)

**Returns:**
- `Tuple[List[ArticleInDB], int]`: Tuple of (list of articles, total count)

---

### `search_articles(query: str, skip: int = 0, limit: int = 10, **filters) -> Tuple[List[ArticleInDB], int]`

Search articles by text query with filtering.

**Parameters:**
- `query` (str): Search query string
- `skip` (int): Number of documents to skip (for pagination)
- `limit` (int): Maximum number of documents to return
- `source_id` (Optional[str]): Filter by source ID
- `start_date` (Optional[datetime]): Filter by start date
- `end_date` (Optional[datetime]): Filter by end date

**Returns:**
- `Tuple[List[ArticleInDB], int]`: Tuple of (list of matching articles, total count)

---

### `update_article_sentiment(article_id: str, sentiment: SentimentAnalysis) -> bool`

Update the sentiment analysis for an article.

**Parameters:**
- `article_id` (str): Article ID
- `sentiment` (SentimentAnalysis): Sentiment analysis data

**Returns:**
- `bool`: True if updated successfully, False otherwise

## Error Handling

The service handles various error conditions:

- **Duplicate Articles**: Returns None when attempting to create a duplicate article
- **Invalid IDs**: Returns None for non-existent article IDs
- **Database Errors**: Logs errors and may raise exceptions for critical failures

## Examples

### Filtering Articles by Date Range

```python
from datetime import datetime, timezone, timedelta

# Get articles from the last 7 days
end_date = datetime.now(timezone.utc)
start_date = end_date - timedelta(days=7)

articles, total = await article_service.list_articles(
    start_date=start_date,
    end_date=end_date,
    limit=20
)
```

### Updating Article Sentiment

```python
from src.crypto_news_aggregator.db.mongodb_models import SentimentAnalysis, SentimentLabel

sentiment = SentimentAnalysis(
    score=0.8,
    magnitude=1.2,
    label=SentimentLabel.POSITIVE,
    subjectivity=0.7
)

success = await article_service.update_article_sentiment(
    article_id="507f1f77bcf86cd799439011",
    sentiment=sentiment
)
```

### Searching for Articles

```python
# Search for articles about Ethereum with positive sentiment
articles, total = await article_service.search_articles(
    query="Ethereum",
    min_sentiment=0.5,
    limit=10
)
```

## Dependencies

- MongoDB (via Motor for async operations)
- Pydantic for data validation
- Python's built-in logging for error tracking
