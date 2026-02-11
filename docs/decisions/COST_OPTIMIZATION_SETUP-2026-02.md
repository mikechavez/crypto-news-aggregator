# Cost Optimization Database Setup Guide

## 🎯 Objective

Set up MongoDB collections and indexes to enable LLM response caching and cost tracking, reducing Anthropic API costs from **$92/month to under $10/month** (89% reduction).

## 📊 Cost Breakdown

### Current State (No Caching)
- **Monthly API Calls**: ~92,000
- **Estimated Cost**: $92/month
- **Cache Hit Rate**: 0%

### Target State (With Caching)
- **Monthly API Calls**: ~9,200
- **Estimated Cost**: <$10/month
- **Cache Hit Rate**: ~90%
- **Savings**: ~$82/month

## 🗄️ Collections Created

### 1. `llm_cache` Collection
Stores cached LLM responses to avoid redundant API calls.

**Schema:**
```javascript
{
  cache_key: String,        // Unique hash of request parameters
  response: Object,         // Cached LLM response
  created_at: Date,         // When cache entry was created
  expires_at: Date,         // When cache entry expires (TTL)
  hit_count: Number,        // Number of times cache was hit
  model: String,            // Model used (e.g., "claude-3-5-haiku-20241022")
  operation: String         // Operation type (e.g., "entity_extraction")
}
```

**Indexes:**
- `cache_key` (unique) - Fast lookups by cache key
- `expires_at` (TTL) - Auto-delete expired entries
- `created_at` (descending) - Analytics queries

### 2. `api_costs` Collection
Tracks API usage and costs for monitoring and optimization.

**Schema:**
```javascript
{
  timestamp: Date,          // When API call was made
  operation: String,        // Operation type (e.g., "entity_extraction")
  model: String,            // Model used
  input_tokens: Number,     // Input tokens consumed
  output_tokens: Number,    // Output tokens generated
  cost_usd: Number,         // Cost in USD
  cached: Boolean,          // Whether response was cached
  cache_key: String         // Cache key if applicable
}
```

**Indexes:**
- `timestamp` (descending) - Recent queries
- `operation` - Filter by operation type
- `model` - Filter by model
- `timestamp + operation` (compound) - Efficient time-based operation queries

## 🚀 Setup Instructions

### Prerequisites

1. **MongoDB Atlas Connection String**
   - Ensure you have your MongoDB Atlas connection string
   - Format: `mongodb+srv://${MONGODB_USER}:${MONGODB_PASSWORD}@cluster.mongodb.net/crypto_news`

2. **Poetry Environment**
   - Poetry installed and configured
   - Dependencies installed: `poetry install`
   - Required packages: `motor` (async MongoDB driver), `certifi`

### Step 1: Set Environment Variable

```bash
export MONGODB_URI="mongodb+srv://${MONGODB_USER}:${MONGODB_PASSWORD}@cluster.mongodb.net/crypto_news"
```

Or add to your `.env` file:
```bash
MONGODB_URI=mongodb+srv://${MONGODB_USER}:${MONGODB_PASSWORD}@cluster.mongodb.net/crypto_news
```

### Step 2: Run Migration Script

```bash
# From project root
poetry run python scripts/setup_cost_optimization.py
```

### Step 3: Verify Output

You should see:

```
============================================================
        Cost Optimization Database Setup
============================================================

ℹ️  Connecting to MongoDB...
✅ Connected to MongoDB successfully

============================================================
          Setting up LLM Cache Collection
============================================================

ℹ️  Creating unique index on cache_key...
✅ Created unique index: cache_key_unique
ℹ️  Creating TTL index on expires_at...
✅ Created TTL index: expires_at_ttl (auto-deletes expired entries)
ℹ️  Creating index on created_at...
✅ Created index: created_at_desc

============================================================
          Setting up API Costs Collection
============================================================

ℹ️  Creating index on timestamp...
✅ Created index: timestamp_desc
ℹ️  Creating index on operation...
✅ Created index: operation_idx
ℹ️  Creating index on model...
✅ Created index: model_idx
ℹ️  Creating compound index on timestamp + operation...
✅ Created compound index: timestamp_operation_compound

============================================================
                  Verifying Setup
============================================================

ℹ️  Testing llm_cache collection...
✅ Inserted test cache entry: 507f1f77bcf86cd799439011
✅ Successfully read back test cache entry
✅ Cleaned up test cache entry
ℹ️  Testing api_costs collection...
✅ Inserted test cost entry: 507f1f77bcf86cd799439012
✅ Successfully read back test cost entry
✅ Cleaned up test cost entry

============================================================
               Database Statistics
============================================================

Total Articles: 1,234
Total Entity Mentions: 5,678
Total Narratives: 89

============================================================
          Cost Optimization Estimates
============================================================

ℹ️  Current Costs (Without Optimization):
  Monthly API Calls: ~92,000
  Estimated Cost: $92/month

ℹ️  Projected Costs (With Caching):
  Cache Hit Rate: ~90%
  Monthly API Calls: ~9,200
  Estimated Cost: <$10/month

ℹ️  Savings:
  API Calls Saved: ~82,800/month
  Cost Savings: ~$82/month (89% reduction)

============================================================
                   Setup Complete!
============================================================

✅ Collections created:
  • llm_cache - LLM response caching
  • api_costs - API cost tracking

✅ Indexes created:
  • llm_cache:
    - cache_key (unique)
    - expires_at (TTL, auto-delete)
    - created_at (descending)
  • api_costs:
    - timestamp (descending)
    - operation
    - model
    - timestamp + operation (compound)

✅ Next Steps:
  1. Implement LLM caching layer in entity extraction
  2. Implement cost tracking in API calls
  3. Add cache warming for common queries
  4. Monitor cache hit rates and costs
```

## 🔍 Verification

### Check Collections Exist

```bash
# Using MongoDB shell
mongosh "your_connection_string"

use crypto_news
show collections
# Should show: llm_cache, api_costs

# Check indexes
db.llm_cache.getIndexes()
db.api_costs.getIndexes()
```

### Check via Python

Create a verification script:

```bash
# Create verify_cost_optimization.py
cat > scripts/verify_cost_optimization.py << 'EOF'
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

async def verify():
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("❌ MONGODB_URI not set")
        return
    
    client = AsyncIOMotorClient(mongodb_uri, tlsCAFile=certifi.where())
    db = client["crypto_news"]
    
    # List collections
    collections = await db.list_collection_names()
    print("✅ Collections:", collections)
    
    # Check llm_cache indexes
    indexes = await db.llm_cache.list_indexes().to_list(None)
    print("\n✅ llm_cache indexes:")
    for idx in indexes:
        print(f"  - {idx['name']}")
    
    # Check api_costs indexes
    indexes = await db.api_costs.list_indexes().to_list(None)
    print("\n✅ api_costs indexes:")
    for idx in indexes:
        print(f"  - {idx['name']}")
    
    client.close()

asyncio.run(verify())
EOF

# Run verification
poetry run python scripts/verify_cost_optimization.py
```

## 📈 Next Steps

### Phase 2: Implement Caching Layer

1. **Create Cache Service** (`src/crypto_news_aggregator/services/llm_cache.py`)
   - Cache key generation
   - Cache hit/miss logic
   - TTL management
   - Hit count tracking

2. **Integrate with Entity Extraction**
   - Wrap Anthropic API calls with cache layer
   - Check cache before API call
   - Store response in cache after API call

3. **Add Cost Tracking**
   - Track all API calls in `api_costs` collection
   - Calculate costs based on token usage
   - Monitor cache effectiveness

### Phase 3: Optimization

1. **Cache Warming**
   - Pre-populate cache with common queries
   - Identify frequently extracted entities

2. **Cache Analytics**
   - Monitor cache hit rates
   - Identify cache misses
   - Optimize cache TTL

3. **Cost Monitoring Dashboard**
   - Daily/weekly/monthly cost reports
   - Cache effectiveness metrics
   - Cost per operation breakdown

## 🛠️ Troubleshooting

### Connection Issues

**Error**: `ServerSelectionTimeoutError`

**Solution**:
- Check MongoDB URI is correct
- Verify network connectivity
- Check MongoDB Atlas IP whitelist

### Index Creation Fails

**Error**: `Index already exists with different options`

**Solution**:
```python
# Drop existing indexes
await db.llm_cache.drop_indexes()
await db.api_costs.drop_indexes()

# Re-run migration script
```

### Permission Issues

**Error**: `not authorized on crypto_news to execute command`

**Solution**:
- Verify MongoDB user has `readWrite` role
- Check database name matches connection string

## 📝 Files

- **Migration Script**: `scripts/setup_cost_optimization.py`
- **This Guide**: `COST_OPTIMIZATION_SETUP.md`

## 🎓 Cache Strategy

### Cache Key Generation

```python
import hashlib
import json

def generate_cache_key(operation: str, model: str, **params) -> str:
    """Generate a unique cache key for an LLM request."""
    key_data = {
        "operation": operation,
        "model": model,
        **params
    }
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(key_string.encode()).hexdigest()
```

### Cache TTL Strategy

| Operation | TTL | Rationale |
|-----------|-----|-----------|
| Entity Extraction | 30 days | Entities rarely change |
| Narrative Discovery | 7 days | Narratives evolve |
| Sentiment Analysis | 24 hours | Sentiment is time-sensitive |

### Cache Invalidation

- **Time-based**: TTL indexes auto-delete expired entries
- **Manual**: Delete cache entries when source data changes
- **Selective**: Clear cache for specific operations/models

## 💡 Best Practices

1. **Monitor Cache Hit Rates**
   - Target: >85% hit rate
   - Alert if hit rate drops below 70%

2. **Track Costs Daily**
   - Set up daily cost reports
   - Alert if daily cost exceeds threshold

3. **Optimize Cache TTL**
   - Start conservative (shorter TTL)
   - Increase TTL as confidence grows

4. **Regular Cleanup**
   - Monitor cache size
   - Adjust TTL if cache grows too large

5. **A/B Testing**
   - Compare cached vs. non-cached responses
   - Ensure cache doesn't degrade quality

## 📊 Success Metrics

- **Cache Hit Rate**: >85%
- **Monthly Cost**: <$10
- **API Calls Saved**: >80,000/month
- **Response Time**: <100ms for cache hits
- **Cache Size**: <1GB

## 🔗 Related Documentation

- [Anthropic API Pricing](https://www.anthropic.com/pricing)
- [MongoDB TTL Indexes](https://docs.mongodb.com/manual/core/index-ttl/)
- [Motor Documentation](https://motor.readthedocs.io/)
