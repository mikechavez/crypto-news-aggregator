# Cost Optimization - Phase 1: Database Setup ✅

## Summary

Successfully created the database migration infrastructure for implementing LLM response caching and cost tracking. This is the foundation for reducing Anthropic API costs from **$92/month to under $10/month** (89% reduction).

## What Was Created

### 1. Migration Script
**File**: `scripts/setup_cost_optimization.py`

A comprehensive async migration script that:
- Connects to MongoDB Atlas
- Creates `llm_cache` collection with TTL indexes
- Creates `api_costs` collection with analytics indexes
- Verifies setup with test entries
- Displays database statistics and cost projections
- Provides colored, user-friendly output

### 2. Documentation

**Main Guide**: `COST_OPTIMIZATION_SETUP.md`
- Complete setup instructions
- Schema definitions
- Verification procedures
- Troubleshooting guide
- Next steps for Phase 2 & 3

**Quick Reference**: `QUICK_REFERENCE_COST_OPTIMIZATION.md`
- One-page setup guide
- Quick commands
- Troubleshooting tips
- Monitoring queries

### 3. Collections & Indexes

#### `llm_cache` Collection
Stores cached LLM responses to avoid redundant API calls.

**Indexes:**
- `cache_key` (unique) - Fast cache lookups
- `expires_at` (TTL, expireAfterSeconds=0) - Auto-delete expired entries
- `created_at` (descending) - Analytics queries

**Schema:**
```javascript
{
  cache_key: String,        // SHA256 hash of request params
  response: Object,         // Cached LLM response
  created_at: Date,         // Creation timestamp
  expires_at: Date,         // Expiration timestamp (TTL)
  hit_count: Number,        // Cache hit counter
  model: String,            // Model used
  operation: String         // Operation type
}
```

#### `api_costs` Collection
Tracks API usage and costs for monitoring.

**Indexes:**
- `timestamp` (descending) - Recent queries
- `operation` - Filter by operation type
- `model` - Filter by model
- `timestamp + operation` (compound) - Efficient time-based queries

**Schema:**
```javascript
{
  timestamp: Date,          // API call timestamp
  operation: String,        // Operation type
  model: String,            // Model used
  input_tokens: Number,     // Input tokens
  output_tokens: Number,    // Output tokens
  cost_usd: Number,         // Cost in USD
  cached: Boolean,          // Cache hit/miss
  cache_key: String         // Cache key if applicable
}
```

## How to Run

### Prerequisites
```bash
# 1. Ensure Poetry environment is ready
poetry install

# 2. Set MongoDB URI (check .env or export)
export MONGODB_URI="mongodb+srv://${MONGODB_USER}:${MONGODB_PASSWORD}@cluster.mongodb.net/crypto_news"
```

### Execute Migration
```bash
# Run the migration script
poetry run python scripts/setup_cost_optimization.py
```

### Expected Output
```
============================================================
        Cost Optimization Database Setup
============================================================

ℹ️  Connecting to MongoDB...
✅ Connected to MongoDB successfully

============================================================
          Setting up LLM Cache Collection
============================================================

✅ Created unique index: cache_key_unique
✅ Created TTL index: expires_at_ttl (auto-deletes expired entries)
✅ Created index: created_at_desc

============================================================
          Setting up API Costs Collection
============================================================

✅ Created index: timestamp_desc
✅ Created index: operation_idx
✅ Created index: model_idx
✅ Created compound index: timestamp_operation_compound

============================================================
                  Verifying Setup
============================================================

✅ Inserted test cache entry
✅ Successfully read back test cache entry
✅ Cleaned up test cache entry
✅ Inserted test cost entry
✅ Successfully read back test cost entry
✅ Cleaned up test cost entry

============================================================
               Database Statistics
============================================================

Total Articles: X,XXX
Total Entity Mentions: X,XXX
Total Narratives: XXX

============================================================
          Cost Optimization Estimates
============================================================

Current Costs (Without Optimization):
  Monthly API Calls: ~92,000
  Estimated Cost: $92/month

Projected Costs (With Caching):
  Cache Hit Rate: ~90%
  Monthly API Calls: ~9,200
  Estimated Cost: <$10/month

Savings:
  API Calls Saved: ~82,800/month
  Cost Savings: ~$82/month (89% reduction)

============================================================
                   Setup Complete!
============================================================
```

## Verification

### Quick Check
```bash
# Verify collections exist
poetry run python -c "
import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

async def check():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'), tlsCAFile=certifi.where())
    db = client['crypto_news']
    collections = await db.list_collection_names()
    print('✅ llm_cache exists:', 'llm_cache' in collections)
    print('✅ api_costs exists:', 'api_costs' in collections)
    client.close()

asyncio.run(check())
"
```

### MongoDB Shell
```javascript
use crypto_news

// Check collections
show collections
// Should include: llm_cache, api_costs

// Check llm_cache indexes
db.llm_cache.getIndexes()

// Check api_costs indexes
db.api_costs.getIndexes()
```

## Files Created

```
scripts/
  └── setup_cost_optimization.py          # Migration script

docs/
  ├── COST_OPTIMIZATION_SETUP.md          # Full documentation
  ├── QUICK_REFERENCE_COST_OPTIMIZATION.md # Quick reference
  └── COST_OPTIMIZATION_PHASE1_COMPLETE.md # This file
```

## Next Steps

### Phase 2: Implement Caching Layer (Next Task)

1. **Create LLM Cache Service**
   - File: `src/crypto_news_aggregator/services/llm_cache.py`
   - Functions:
     - `generate_cache_key()` - Create unique cache keys
     - `get_cached_response()` - Check cache before API call
     - `store_response()` - Save API response to cache
     - `track_cost()` - Log API costs

2. **Integrate with Entity Extraction**
   - File: `src/crypto_news_aggregator/services/entity_extraction.py`
   - Wrap Anthropic API calls with cache layer
   - Track costs for all API calls

3. **Add Cost Tracking to Narrative Discovery**
   - File: `src/crypto_news_aggregator/services/narrative_themes.py`
   - Implement caching for narrative discovery
   - Track costs per operation

### Phase 3: Monitoring & Optimization

1. **Cache Analytics Dashboard**
   - Cache hit rate monitoring
   - Cost per operation breakdown
   - Daily/weekly/monthly reports

2. **Cache Warming**
   - Pre-populate cache with common queries
   - Identify frequently extracted entities

3. **Cache Optimization**
   - Adjust TTL based on cache effectiveness
   - Implement cache invalidation strategies

## Cost Projections

### Current State (No Caching)
- **Entity Extraction**: ~80,000 calls/month
- **Narrative Discovery**: ~12,000 calls/month
- **Total**: ~92,000 calls/month
- **Cost**: ~$92/month

### Target State (90% Cache Hit Rate)
- **Cache Hits**: ~82,800 calls/month (free)
- **Cache Misses**: ~9,200 calls/month (paid)
- **Cost**: <$10/month
- **Savings**: ~$82/month (89% reduction)

### ROI Timeline
- **Month 1**: Setup + initial caching (~50% hit rate) → ~$46 cost
- **Month 2**: Cache warmed up (~80% hit rate) → ~$18 cost
- **Month 3+**: Optimized (~90% hit rate) → <$10 cost
- **Annual Savings**: ~$984/year

## Technical Details

### Cache Key Generation Strategy
```python
import hashlib
import json

def generate_cache_key(operation: str, model: str, **params) -> str:
    """Generate SHA256 hash of normalized request parameters."""
    key_data = {
        "operation": operation,
        "model": model,
        **params
    }
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(key_string.encode()).hexdigest()
```

### TTL Strategy
| Operation | TTL | Rationale |
|-----------|-----|-----------|
| Entity Extraction | 30 days | Entities rarely change |
| Narrative Discovery | 7 days | Narratives evolve |
| Sentiment Analysis | 24 hours | Time-sensitive |

### Cache Invalidation
- **Automatic**: TTL indexes auto-delete expired entries
- **Manual**: Delete cache when source data changes
- **Selective**: Clear cache for specific operations/models

## Success Metrics

### Phase 1 (Current) ✅
- [x] Collections created
- [x] Indexes created
- [x] Migration script tested
- [x] Documentation complete

### Phase 2 (Next)
- [ ] Cache service implemented
- [ ] Entity extraction integrated
- [ ] Narrative discovery integrated
- [ ] Cost tracking active

### Phase 3 (Future)
- [ ] Cache hit rate >85%
- [ ] Monthly cost <$10
- [ ] Monitoring dashboard live
- [ ] Cache warming implemented

## Deployment Checklist

### Pre-Deployment
- [x] Migration script created
- [x] Documentation complete
- [x] Script tested locally
- [ ] MongoDB URI configured in production
- [ ] Backup current database (optional)

### Deployment
- [ ] Create feature branch: `feature/cost-optimization-phase1`
- [ ] Commit changes with conventional commit message
- [ ] Create PR with description
- [ ] Review and merge to main
- [ ] Run migration on production database
- [ ] Verify collections and indexes created

### Post-Deployment
- [ ] Monitor MongoDB Atlas for new collections
- [ ] Verify indexes are being used
- [ ] Check for any errors in logs
- [ ] Document any issues encountered

## Troubleshooting

### Common Issues

**Issue**: `MONGODB_URI environment variable not set`
```bash
# Solution: Set the environment variable
export MONGODB_URI="mongodb+srv://..."
# Or add to .env file
```

**Issue**: `ServerSelectionTimeoutError`
```bash
# Solutions:
# 1. Check MongoDB URI is correct
# 2. Verify network connectivity
# 3. Add your IP to MongoDB Atlas whitelist
# 4. Check firewall settings
```

**Issue**: `Index already exists with different options`
```bash
# Solution: Drop existing indexes and re-run
poetry run python -c "
import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

async def reset():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'), tlsCAFile=certifi.where())
    db = client['crypto_news']
    await db.llm_cache.drop_indexes()
    await db.api_costs.drop_indexes()
    print('✅ Indexes dropped. Re-run setup script.')
    client.close()

asyncio.run(reset())
"
```

## References

- **Migration Script**: `scripts/setup_cost_optimization.py`
- **Full Documentation**: `COST_OPTIMIZATION_SETUP.md`
- **Quick Reference**: `QUICK_REFERENCE_COST_OPTIMIZATION.md`
- **Development Rules**: `.windsurf/windsurf-rules.md`
- **API Retry Logic**: `QUICK_REFERENCE_API_RETRY.md`

## Notes

- All scripts use Poetry for dependency management
- MongoDB connection uses SSL/TLS with certifi
- TTL indexes automatically delete expired cache entries
- Cost tracking enables data-driven optimization decisions
- Cache hit rate target: >85% for optimal savings

---

**Status**: ✅ Phase 1 Complete - Ready for Phase 2 Implementation
**Date**: November 10, 2025
**Next Task**: Implement LLM caching service and integrate with entity extraction
