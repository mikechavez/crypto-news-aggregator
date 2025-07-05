# Articles API Reference

This document provides detailed information about the Articles API endpoints available in the Crypto News Aggregator application. These endpoints allow you to manage and retrieve news articles from various cryptocurrency news sources.

## Base URL

All API endpoints are relative to the base URL:
```
https://api.yourdomain.com/api/v1
```

## Authentication

All endpoints require authentication. Include your API key in the request header:
```
Authorization: Bearer your_api_key_here
```

## Response Format

All API responses follow this format:

```json
{
  "data": [
    // Array of resources
  ],
  "total": 42,
  "page": 1,
  "limit": 10
}
```

Error responses follow this format:

```json
{
  "detail": "Error message describing the issue"
}
```

## Endpoints

### List Articles

```
GET /articles/
```

Retrieves a paginated list of articles with optional filtering.

#### Query Parameters

| Parameter    | Type      | Required | Description                                      |
|--------------|-----------|----------|--------------------------------------------------|
| skip         | integer   | No       | Number of items to skip (default: 0)            |
| limit        | integer   | No       | Maximum number of items to return (default: 10, max: 100) |
| source_id    | string    | No       | Filter by source ID                              |
| start_date   | ISO 8601  | No       | Filter by published date (greater than or equal) |
| end_date     | ISO 8601  | No       | Filter by published date (less than or equal)    |
| keywords     | string    | No       | Comma-separated list of keywords to filter by    |
| min_sentiment| float     | No       | Minimum sentiment score (-1 to 1)                |
| max_sentiment| float     | No       | Maximum sentiment score (-1 to 1)                |

#### Example Request

```http
GET /api/v1/articles/?source_id=coindesk&start_date=2023-01-01T00:00:00Z&limit=5
```

#### Example Response (200 OK)

```json
{
  "data": [
    {
      "id": "507f1f77bcf86cd799439011",
      "title": "Bitcoin Reaches New All-Time High",
      "description": "Bitcoin has reached a new all-time high price of $100,000...",
      "url": "https://example.com/bitcoin-all-time-high",
      "source": {
        "id": "coindesk",
        "name": "CoinDesk"
      },
      "published_at": "2023-01-15T08:30:00Z",
      "sentiment": {
        "score": 0.85,
        "magnitude": 1.2,
        "label": "positive"
      }
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 5
}
```

#### Response Headers

| Header          | Description                          |
|-----------------|--------------------------------------|
| X-Total-Count   | Total number of matching articles    |
| X-Page          | Current page number                  |
| X-Per-Page      | Number of items per page             |

---

### Get Article by ID

```
GET /articles/{article_id}
```

Retrieves a single article by its ID.

#### Path Parameters

| Parameter | Type   | Required | Description            |
|-----------|--------|----------|------------------------|
| article_id| string | Yes      | The ID of the article  |

#### Example Request

```http
GET /api/v1/articles/507f1f77bcf86cd799439011
```

#### Example Response (200 OK)

```json
{
  "data": {
    "id": "507f1f77bcf86cd799439011",
    "title": "Bitcoin Reaches New All-Time High",
    "description": "Bitcoin has reached a new all-time high price of $100,000...",
    "content": "Full article content here...",
    "url": "https://example.com/bitcoin-all-time-high",
    "url_to_image": "https://example.com/images/bitcoin.jpg",
    "author": "John Doe",
    "source": {
      "id": "coindesk",
      "name": "CoinDesk"
    },
    "published_at": "2023-01-15T08:30:00Z",
    "sentiment": {
      "score": 0.85,
      "magnitude": 1.2,
      "label": "positive",
      "subjectivity": 0.7
    },
    "keywords": ["bitcoin", "cryptocurrency", "trading"],
    "created_at": "2023-01-15T08:30:00Z",
    "updated_at": "2023-01-15T08:30:00Z"
  }
}
```

#### Error Responses

| Status Code | Error           | Description                          |
|-------------|-----------------|--------------------------------------|
| 404         | Article not found | The specified article was not found  |
| 400         | Invalid ID format | The provided ID is not valid        |

---

### Search Articles

```
GET /articles/search
```

Searches articles by text query with full-text search capabilities.

#### Query Parameters

| Parameter    | Type      | Required | Description                                      |
|--------------|-----------|----------|--------------------------------------------------|
| q            | string    | Yes      | Search query string                              |
| skip         | integer   | No       | Number of items to skip (default: 0)            |
| limit        | integer   | No       | Maximum number of items to return (default: 10, max: 100) |
| source_id    | string    | No       | Filter by source ID                              |
| start_date   | ISO 8601  | No       | Filter by published date (greater than or equal) |
| end_date     | ISO 8601  | No       | Filter by published date (less than or equal)    |

#### Example Request

```http
GET /api/v1/articles/search?q=bitcoin+ethereum&source_id=coindesk&limit=5
```

#### Example Response (200 OK)

```json
{
  "data": [
    {
      "id": "507f1f77bcf86cd799439011",
      "title": "Bitcoin and Ethereum Show Strong Correlation",
      "description": "Analysis shows increasing correlation between Bitcoin and Ethereum prices...",
      "url": "https://example.com/btc-eth-correlation",
      "source": {
        "id": "coindesk",
        "name": "CoinDesk"
      },
      "published_at": "2023-01-15T08:30:00Z",
      "score": 12.345
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 5
}
```

---

### Get Trending Keywords

```
GET /articles/trending/keywords
```

Retrieves currently trending keywords from recent articles.

#### Query Parameters

| Parameter    | Type      | Required | Description                                      |
|--------------|-----------|----------|--------------------------------------------------|
| hours        | integer   | No       | Time window in hours (1-168, default: 24)       |
| limit        | integer   | No       | Maximum number of keywords to return (default: 10, max: 50) |
| min_mentions | integer   | No       | Minimum number of mentions (default: 2)          |

#### Example Request

```http
GET /api/v1/articles/trending/keywords?hours=24&limit=5
```

#### Example Response (200 OK)

```json
{
  "data": [
    {
      "keyword": "bitcoin",
      "count": 42
    },
    {
      "keyword": "ethereum",
      "count": 35
    },
    {
      "keyword": "defi",
      "count": 28
    },
    {
      "keyword": "nft",
      "count": 25
    },
    {
      "keyword": "regulation",
      "count": 20
    }
  ]
}
```

---

### Get Sentiment Trends

```
GET /articles/sentiment/trends
```

Retrieves sentiment trends over time for articles.

#### Query Parameters

| Parameter    | Type      | Required | Description                                      |
|--------------|-----------|----------|--------------------------------------------------|
| hours        | integer   | No       | Time window in hours (1-168, default: 24)       |
| interval     | integer   | No       | Time interval in hours (1-24, default: 1)       |

#### Example Request

```http
GET /api/v1/articles/sentiment/trends?hours=24&interval=2
```

#### Example Response (200 OK)

```json
{
  "data": {
    "timestamps": [
      "2023-01-15T00:00:00Z",
      "2023-01-15T02:00:00Z",
      "2023-01-15T04:00:00Z",
      "2023-01-15T06:00:00Z",
      "2023-01-15T08:00:00Z",
      "2023-01-15T10:00:00Z",
      "2023-01-15T12:00:00Z",
      "2023-01-15T14:00:00Z",
      "2023-01-15T16:00:00Z",
      "2023-01-15T18:00:00Z",
      "2023-01-15T20:00:00Z",
      "2023-01-15T22:00:00Z"
    ],
    "scores": [
      0.12,
      0.15,
      0.18,
      0.22,
      0.25,
      0.28,
      0.31,
      0.35,
      0.38,
      0.42,
      0.45,
      0.48
    ],
    "counts": [
      15,
      18,
      22,
      25,
      30,
      32,
      35,
      38,
      40,
      42,
      45,
      48
    ]
  }
}
```

## Rate Limiting

API requests are subject to rate limiting:

- 100 requests per minute per API key
- 1,000 requests per hour per API key
- 10,000 requests per day per API key

Rate limit headers are included in all responses:

| Header                | Description                               |
|-----------------------|-------------------------------------------|
| X-RateLimit-Limit     | Maximum number of requests allowed        |
| X-RateLimit-Remaining| Remaining number of requests in window    |
| X-RateLimit-Reset     | Time when the rate limit resets (UTC)     |

## Error Handling

### Common Error Responses

| Status Code | Error Code          | Description                               |
|-------------|---------------------|-------------------------------------------|
| 400         | BAD_REQUEST         | Invalid request parameters                |
| 401         | UNAUTHORIZED        | Missing or invalid API key                |
| 403         | FORBIDDEN           | Insufficient permissions                  |
| 404         | NOT_FOUND           | Resource not found                        |
| 429         | TOO_MANY_REQUESTS   | Rate limit exceeded                       |
| 500         | INTERNAL_ERROR      | Internal server error                     |

### Example Error Response

```json
{
  "detail": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again in 42 seconds.",
    "retry_after": 42
  }
}
```

## Best Practices

1. **Use Pagination**: Always use `skip` and `limit` parameters when fetching lists of articles
2. **Filter When Possible**: Use available query parameters to filter results on the server side
3. **Handle Rate Limits**: Implement proper error handling for rate limit responses
4. **Use Appropriate Timeouts**: Set reasonable timeouts for API requests (recommended: 30 seconds)
5. **Cache Responses**: Cache API responses when appropriate to reduce server load
6. **Use Conditional Requests**: Implement ETag or Last-Modified headers for efficient caching

## Versioning

API versioning is handled through the URL path. The current version is `v1`.

Example: `https://api.yourdomain.com/api/v1/articles`

## Support

For support, please contact [support@yourdomain.com](mailto:support@yourdomain.com) or visit our [developer portal](https://developers.yourdomain.com).
