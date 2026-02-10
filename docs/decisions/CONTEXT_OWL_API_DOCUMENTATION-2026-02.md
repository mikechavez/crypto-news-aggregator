# Context Owl - OpenAI Compatible API Documentation

## Overview
Context Owl is a sophisticated cryptocurrency news aggregation and analysis platform that provides OpenAI-compatible API endpoints for seamless integration with AI applications and services.

## Base URL
```
https://your-domain.com
```

## Authentication
The API supports two authentication methods:

### 1. API Key Authentication
Use the `X-API-Key` header with your API key:
```
X-API-Key: your-api-key-here
```

### 2. Bearer Token Authentication
Use the `Authorization` header with a Bearer token:
```
Authorization: Bearer your-jwt-token-here
```

## Endpoints

### Chat Completions
**Endpoint:** `POST /v1/chat/completions`

OpenAI-compatible chat completions endpoint with cryptocurrency analysis capabilities.

#### Request Format
```json
{
  "model": "crypto-insight-agent",
  "messages": [
    {
      "role": "user",
      "content": "What is the current price of Bitcoin?"
    }
  ],
  "stream": false
}
```

#### Response Format
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Bitcoin is currently trading at $50,000 with strong upward momentum."
      },
      "finish_reason": "stop"
    }
  ]
}
```

#### Streaming Response
Set `"stream": true` for Server-Sent Events (SSE) streaming:
```json
{
  "model": "crypto-insight-agent",
  "messages": [
    {
      "role": "user",
      "content": "Tell me about Bitcoin"
    }
  ],
  "stream": true
}
```

Streaming response format:
```
data: {"choices": [{"delta": {"role": "assistant", "content": "Bitcoin is..."}, "finish_reason": null}]}

data: {"choices": [{"delta": {"content": " a decentralized..."}, "finish_reason": null}]}

data: [DONE]
```

## Supported Query Types

### 1. Price Inquiries
**Examples:**
- "What is the current price of Bitcoin?"
- "How much is Ethereum worth?"
- "Tell me the value of SOL"

**Response:** Detailed price analysis with market commentary

### 2. Sentiment Analysis
**Examples:**
- "What is the sentiment around Bitcoin?"
- "How do people feel about Ethereum?"
- "Is the market positive about crypto?"

**Response:** Current market sentiment based on recent news articles

### 3. Correlation Analysis
**Examples:**
- "How correlated is Bitcoin with other cryptocurrencies?"
- "What is the relationship between BTC and ETH?"
- "Show me correlation data for crypto"

**Response:** Price correlation data between different cryptocurrencies

## Supported Cryptocurrencies
- **BTC** - Bitcoin
- **ETH** - Ethereum
- **SOL** - Solana
- **DOGE** - Dogecoin
- **ADA** - Cardano
- **XRP** - Ripple
- **DOT** - Polkadot
- **LINK** - Chainlink

## Error Handling
The API follows standard HTTP status codes:

- **200** - Success
- **400** - Bad Request (invalid input)
- **401** - Unauthorized (missing/invalid API key)
- **403** - Forbidden (invalid API key)
- **422** - Unprocessable Entity (invalid JSON)
- **500** - Internal Server Error

## Rate Limits
- API keys have configurable rate limits
- Contact support for higher rate limit tiers

## Performance
- **Response Time:** Sub 2-3 seconds for non-streaming requests
- **Streaming:** Real-time responses for live applications
- **Availability:** 99.9% uptime SLA

## Integration Examples

### Python
```python
import requests

url = "https://your-domain.com/v1/chat/completions"
headers = {
    "X-API-Key": "your-api-key",
    "Content-Type": "application/json"
}
data = {
    "model": "crypto-insight-agent",
    "messages": [
        {
            "role": "user",
            "content": "What is the current sentiment around Bitcoin?"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)
result = response.json()
print(result["choices"][0]["message"]["content"])
```

### JavaScript/Node.js
```javascript
const response = await fetch('https://your-domain.com/v1/chat/completions', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'crypto-insight-agent',
    messages: [
      {
        role: 'user',
        content: 'What is the price of Ethereum?'
      }
    ]
  })
});

const result = await response.json();
console.log(result.choices[0].message.content);
```

### Streaming Example (Python)
```python
import requests
import json

url = "https://your-domain.com/v1/chat/completions"
headers = {
    "X-API-Key": "your-api-key",
    "Content-Type": "application/json"
}
data = {
    "model": "crypto-insight-agent",
    "messages": [
        {
            "role": "user",
            "content": "Tell me about Bitcoin in detail"
        }
    ],
    "stream": true
}

response = requests.post(url, headers=headers, json=data, stream=True)
for line in response.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith('data: '):
            if line == 'data: [DONE]':
                break
            chunk = json.loads(line[6:])
            if chunk["choices"][0]["delta"].get("content"):
                print(chunk["choices"][0]["delta"]["content"], end="")
```

## Features

### ✅ Completed Features
- [x] OpenAI-compatible `/v1/chat/completions` endpoint
- [x] API key authentication
- [x] Bearer token authentication
- [x] Streaming responses (SSE)
- [x] Price inquiry functionality
- [x] Sentiment analysis
- [x] Correlation analysis
- [x] Symbol extraction from natural language
- [x] Intent classification
- [x] Comprehensive error handling
- [x] Performance monitoring
- [x] Response format validation
- [x] Integration testing

### 🚀 Performance Metrics
- **Response Time:** < 2-3 seconds
- **Availability:** 99.9%
- **Data Freshness:** Real-time market data
- **Articles Processed:** 61+ enriched articles
- **Concurrent Users:** Supports high load

## Support
For technical support or partnership inquiries, please contact the development team.

## Version
API Version: 1.0.0
Last Updated: 2025-09-25
