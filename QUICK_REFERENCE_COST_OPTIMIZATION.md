# Quick Reference: Cost Optimization Setup

## 🎯 Goal
Reduce Anthropic API costs from **$92/month → <$10/month** (89% savings)

## 📋 Quick Start

```bash
# 1. Ensure Poetry environment is ready
poetry install

# 2. Set MongoDB URI (if not in .env)
export MONGODB_URI="your_mongodb_atlas_connection_string"

# 3. Run migration
poetry run python scripts/setup_cost_optimization.py

# 4. Verify (optional)
poetry run python scripts/verify_cost_optimization.py
```

## 📊 What Gets Created

### Collections
- **`llm_cache`** - Stores cached LLM responses
- **`api_costs`** - Tracks API usage and costs

### Indexes

**llm_cache:**
- `cache_key` (unique) - Fast lookups
- `expires_at` (TTL) - Auto-delete expired entries
- `created_at` (desc) - Analytics

**api_costs:**
- `timestamp` (desc) - Recent queries
- `operation` - Filter by operation
- `model` - Filter by model
- `timestamp + operation` (compound) - Efficient queries

## ✅ Success Indicators

```
✅ Connected to MongoDB successfully
✅ Created unique index: cache_key_unique
✅ Created TTL index: expires_at_ttl
✅ Inserted test cache entry
✅ Successfully read back test cache entry
✅ Setup Complete!
```

## 🔍 Verification Commands

```bash
# Check collections exist
poetry run python -c "
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

async def check():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'), tlsCAFile=certifi.where())
    db = client['crypto_news']
    collections = await db.list_collection_names()
    print('llm_cache exists:', 'llm_cache' in collections)
    print('api_costs exists:', 'api_costs' in collections)
    client.close()

asyncio.run(check())
"
```

## 📈 Expected Results

### Database Statistics
- Shows current article, entity, and narrative counts
- Displays before/after cost estimates

### Cost Projections
| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| Monthly API Calls | 92,000 | 9,200 | 82,800 |
| Monthly Cost | $92 | <$10 | ~$82 |
| Cache Hit Rate | 0% | ~90% | - |

## 🚨 Troubleshooting

### "MONGODB_URI environment variable not set"
```bash
# Check if set
echo $MONGODB_URI

# Set it
export MONGODB_URI="mongodb+srv://..."

# Or add to .env file
echo 'MONGODB_URI=mongodb+srv://...' >> .env
```

### "ServerSelectionTimeoutError"
- Check MongoDB URI is correct
- Verify network connectivity
- Check MongoDB Atlas IP whitelist (add your IP)

### "Index already exists with different options"
```bash
# Drop and recreate (use with caution)
poetry run python -c "
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

async def reset():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'), tlsCAFile=certifi.where())
    db = client['crypto_news']
    await db.llm_cache.drop_indexes()
    await db.api_costs.drop_indexes()
    print('Indexes dropped. Re-run setup script.')
    client.close()

asyncio.run(reset())
"
```

## 📝 Files Created

- `scripts/setup_cost_optimization.py` - Migration script
- `COST_OPTIMIZATION_SETUP.md` - Full documentation
- `QUICK_REFERENCE_COST_OPTIMIZATION.md` - This file

## 🎯 Next Steps

1. ✅ **Phase 1: Database Setup** (this task)
   - Create collections and indexes

2. 🔄 **Phase 2: Implement Caching**
   - Create `llm_cache.py` service
   - Integrate with entity extraction
   - Add cost tracking

3. 📊 **Phase 3: Monitoring**
   - Track cache hit rates
   - Monitor daily costs
   - Optimize cache TTL

## 💡 Cache Strategy

### TTL (Time To Live)
| Operation | TTL | Why |
|-----------|-----|-----|
| Entity Extraction | 30 days | Entities stable |
| Narrative Discovery | 7 days | Narratives evolve |
| Sentiment Analysis | 24 hours | Time-sensitive |

### Cache Key Format
```python
# SHA256 hash of:
{
  "operation": "entity_extraction",
  "model": "claude-3-5-haiku-20241022",
  "article_id": "507f1f77bcf86cd799439011",
  "content_hash": "abc123..."
}
```

## 📊 Monitoring Queries

### Check cache hit rate
```javascript
// MongoDB shell
use crypto_news

// Total cache entries
db.llm_cache.countDocuments()

// Cache hits in last 24h
db.api_costs.aggregate([
  { $match: { 
    timestamp: { $gte: new Date(Date.now() - 24*60*60*1000) }
  }},
  { $group: {
    _id: "$cached",
    count: { $sum: 1 }
  }}
])
```

### Check daily costs
```javascript
// Costs for today
db.api_costs.aggregate([
  { $match: {
    timestamp: { $gte: new Date(new Date().setHours(0,0,0,0)) }
  }},
  { $group: {
    _id: null,
    total_cost: { $sum: "$cost_usd" },
    total_calls: { $sum: 1 },
    cached_calls: { 
      $sum: { $cond: ["$cached", 1, 0] }
    }
  }}
])
```

## 🔗 Related Docs

- Full Guide: `COST_OPTIMIZATION_SETUP.md`
- API Retry Logic: `QUICK_REFERENCE_API_RETRY.md`
- Development Rules: `.windsurf/windsurf-rules.md`

## ⚡ One-Liner Setup

```bash
poetry install && export MONGODB_URI="your_uri" && poetry run python scripts/setup_cost_optimization.py
```
