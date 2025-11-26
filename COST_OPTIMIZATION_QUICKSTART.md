# Cost Optimization - Quick Start Card

## ⚡ Run Migration (3 Steps)

```bash
# 1. Install dependencies
poetry install

# 2. Set MongoDB URI (if not in .env)
export MONGODB_URI="mongodb+srv://${MONGODB_USER}:${MONGODB_PASSWORD}@cluster.mongodb.net/crypto_news"

# 3. Run migration
poetry run python scripts/setup_cost_optimization.py
```

## ✅ Success Looks Like

```
✅ Connected to MongoDB successfully
✅ Created unique index: cache_key_unique
✅ Created TTL index: expires_at_ttl
✅ Inserted test cache entry
✅ Setup Complete!
```

## 📊 What You Get

- **`llm_cache`** collection with auto-expiring entries
- **`api_costs`** collection for cost tracking
- **89% cost reduction** potential ($92 → <$10/month)

## 📁 Files Created

| File | Purpose |
|------|---------|
| `scripts/setup_cost_optimization.py` | Migration script |
| `COST_OPTIMIZATION_SETUP.md` | Full documentation |
| `QUICK_REFERENCE_COST_OPTIMIZATION.md` | Quick reference |
| `COST_OPTIMIZATION_PHASE1_COMPLETE.md` | Completion summary |

## 🔍 Verify Setup

```bash
poetry run python -c "
import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

async def check():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'), tlsCAFile=certifi.where())
    db = client['crypto_news']
    collections = await db.list_collection_names()
    print('llm_cache:', 'llm_cache' in collections)
    print('api_costs:', 'api_costs' in collections)
    client.close()

asyncio.run(check())
"
```

## 🚨 Troubleshooting

| Error | Fix |
|-------|-----|
| `MONGODB_URI not set` | `export MONGODB_URI="..."` |
| `ServerSelectionTimeoutError` | Check MongoDB Atlas IP whitelist |
| `Index already exists` | Drop indexes and re-run |

## 📈 Next Steps

**Phase 2**: Implement caching layer
- Create `llm_cache.py` service
- Integrate with entity extraction
- Add cost tracking

**Phase 3**: Monitor & optimize
- Track cache hit rates
- Monitor daily costs
- Optimize TTL settings

## 💰 Cost Impact

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| Monthly API Calls | 92,000 | 9,200 | 82,800 |
| Monthly Cost | $92 | <$10 | ~$82 |
| Cache Hit Rate | 0% | ~90% | - |

## 📚 Documentation

- **Full Guide**: `COST_OPTIMIZATION_SETUP.md`
- **Quick Ref**: `QUICK_REFERENCE_COST_OPTIMIZATION.md`
- **Summary**: `COST_OPTIMIZATION_PHASE1_COMPLETE.md`
