# FEATURE-015: Database Safety Hardening

## Context
- **ADR:** None (Infrastructure hardening)
- **Sprint:** Sprint 3 (Data Quality & Stability)
- **Priority:** P1 (High - Prevents Silent Failures)
- **Estimate:** 15-30 minutes
- **Parent Investigation:** FEATURE-014 (Database connection issue discovered)

## Background

During FEATURE-014 investigation, we discovered scripts were silently connecting to the wrong database (`backdrop` instead of `crypto_news`). MongoDB doesn't error when you connect to the wrong database - it just returns empty results or creates empty databases on first access.

This caused hours of debugging confusion and could happen again in the future if:
- Environment variables are misconfigured
- Database URIs are copy-pasted incorrectly
- Multiple databases exist (dev, test, prod)

**Current Risk:**
- No validation that we're connecting to the correct database
- Silent failures waste developer time
- Could accidentally write to wrong database
- No fast-fail mechanism on startup

## What to Build

Add database name validation to MongoDB connection initialization:

1. Parse database name from `MONGODB_URI`
2. Validate it matches expected production database name (`crypto_news`)
3. Hard-fail with clear error message if mismatch
4. Run check once at application startup (zero runtime cost)

**Expected behavior:**
```python
# Correct database
MONGODB_URI = "mongodb://localhost:27017/crypto_news"
# ✅ App starts normally

# Wrong database
MONGODB_URI = "mongodb://localhost:27017/test"
# ❌ App crashes immediately:
# "FATAL: Expected database 'crypto_news' but got 'test'. Check MONGODB_URI."
```

## Files to Modify

**Primary:**
- `src/crypto_news_aggregator/database.py` (or wherever MongoDB client is initialized)
  - Add database name validation
  - Raise `ValueError` if wrong database
  - Log clear error message

**If database.py doesn't exist, check:**
- `src/crypto_news_aggregator/core/config.py` - Database connection setup
- `src/crypto_news_aggregator/db/connection.py` - Client initialization
- `src/crypto_news_aggregator/__init__.py` - App startup

## Implementation Details

### Step 1: Add Database Validation Function

```python
from urllib.parse import urlparse
import os

def validate_database_connection():
    """
    Validate that MONGODB_URI points to the correct database.
    
    Raises:
        ValueError: If database name doesn't match expected 'crypto_news'
    """
    uri = os.getenv("MONGODB_URI")
    
    if not uri:
        raise ValueError("MONGODB_URI environment variable not set")
    
    # Parse database name from URI
    parsed = urlparse(uri)
    db_name = parsed.path.lstrip('/')
    
    # Extract db_name from query string if present (e.g., ?authSource=dbname)
    if '?' in db_name:
        db_name = db_name.split('?')[0]
    
    # Validate against expected database
    EXPECTED_DB = "crypto_news"
    
    if db_name != EXPECTED_DB:
        raise ValueError(
            f"FATAL: Database name mismatch!\n"
            f"  Expected: '{EXPECTED_DB}'\n"
            f"  Got: '{db_name}'\n"
            f"  Check MONGODB_URI environment variable.\n"
            f"  URI: {uri[:50]}...{uri[-20:]}"
        )
    
    print(f"✅ Database validation passed: Using '{db_name}'")
    return db_name
```

### Step 2: Integrate into MongoDB Client Initialization

**Option A: In `database.py` (or similar):**
```python
from motor.motor_asyncio import AsyncIOMotorClient

def get_mongo_client():
    """Get MongoDB client with database validation."""
    # Validate first
    db_name = validate_database_connection()
    
    # Then connect
    uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(uri)
    
    return client, db_name
```

**Option B: In app startup (e.g., `__init__.py` or `main.py`):**
```python
# At application startup (before any database operations)
def init_app():
    """Initialize application with safety checks."""
    # Validate database first (fail fast)
    validate_database_connection()
    
    # Continue with normal initialization
    client = get_mongo_client()
    # ... rest of startup
```

### Step 3: Test Validation

```bash
# Test 1: Correct database (should pass)
export MONGODB_URI="mongodb://localhost:27017/crypto_news"
python -c "from src.crypto_news_aggregator.database import validate_database_connection; validate_database_connection()"
# Expected: ✅ Database validation passed: Using 'crypto_news'

# Test 2: Wrong database (should fail)
export MONGODB_URI="mongodb://localhost:27017/test"
python -c "from src.crypto_news_aggregator.database import validate_database_connection; validate_database_connection()"
# Expected: ValueError with clear error message

# Test 3: Missing URI (should fail)
unset MONGODB_URI
python -c "from src.crypto_news_aggregator.database import validate_database_connection; validate_database_connection()"
# Expected: ValueError: MONGODB_URI environment variable not set
```

## Acceptance Criteria

- [x] Database name validation function implemented
- [x] Validation runs at application startup (before any DB operations)
- [x] Clear error message when wrong database detected
- [x] Error includes: expected name, actual name, URI excerpt
- [x] Application fails fast (crashes immediately, not silently)
- [x] No runtime performance impact (check runs once at startup)
- [x] Works with MongoDB Atlas URIs (handles query params like `?authSource=admin`)
- [x] Tested with correct database (passes)
- [x] Tested with wrong database (fails with clear message)
- [x] Tested with missing URI (fails with clear message)

## Out of Scope

- Multi-database support (we only use `crypto_news`)
- Database existence validation (MongoDB creates on first write)
- Connection health checks (separate concern)
- Database migration validation (separate concern)

## Dependencies

**Blocked by:** None
**Blocks:** Future database confusion issues

## Testing Requirements

### Unit Tests
```python
# tests/test_database.py

def test_validate_database_connection_success():
    """Test validation passes with correct database name."""
    os.environ["MONGODB_URI"] = "mongodb://localhost:27017/crypto_news"
    db_name = validate_database_connection()
    assert db_name == "crypto_news"

def test_validate_database_connection_wrong_db():
    """Test validation fails with wrong database name."""
    os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test"
    with pytest.raises(ValueError, match="Expected: 'crypto_news'"):
        validate_database_connection()

def test_validate_database_connection_missing_uri():
    """Test validation fails when URI not set."""
    if "MONGODB_URI" in os.environ:
        del os.environ["MONGODB_URI"]
    with pytest.raises(ValueError, match="MONGODB_URI environment variable not set"):
        validate_database_connection()

def test_validate_database_connection_with_query_params():
    """Test validation works with MongoDB Atlas URIs."""
    os.environ["MONGODB_URI"] = "mongodb+srv://user:pass@cluster.mongodb.net/crypto_news?retryWrites=true"
    db_name = validate_database_connection()
    assert db_name == "crypto_news"
```

### Manual Testing
```bash
# From repo root: /Users/mc/dev-projects/crypto-news-aggregator

# 1. Test with correct database
export MONGODB_URI="mongodb://localhost:27017/crypto_news"
python -m crypto_news_aggregator.services.narrative_service
# Expected: App starts normally

# 2. Test with wrong database  
export MONGODB_URI="mongodb://localhost:27017/test"
python -m crypto_news_aggregator.services.narrative_service
# Expected: Immediate crash with clear error

# 3. Restore correct URI
export MONGODB_URI="mongodb://localhost:27017/crypto_news"
```

## Success Metrics

- ✅ Validation function added and tested
- ✅ Application fails fast on database mismatch
- ✅ Error message clearly identifies the problem
- ✅ No performance impact (runs once at startup)
- ✅ Prevents silent "wrong database" failures
- ✅ Saves developer debugging time

## Environment Variables Required

- `MONGODB_URI` - MongoDB connection string (must include database name)

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/015-database-safety-hardening

# Implement validation
# Add tests
# Test manually

git add src/crypto_news_aggregator/database.py
git add tests/test_database.py

git commit -m "feat(database): add database name validation

- Parse and validate database name from MONGODB_URI
- Fail fast if connected to wrong database
- Prevents silent failures from misconfigured URIs
- Adds comprehensive tests for validation logic

Resolves: FEATURE-015"

git push origin feature/015-database-safety-hardening

# Create PR with:
# - Before/After examples of error messages
# - Test results showing validation working
# - Note that this prevents FEATURE-014 type issues
```

## Quick Reference

**Expected Database:** `crypto_news`

**Invalid Databases:**
- `backdrop` (old name from FEATURE-014)
- `test` (development/testing)
- `local` (MongoDB default)
- `admin` (MongoDB system database)

**URI Examples:**

✅ Valid:
```
mongodb://localhost:27017/crypto_news
mongodb+srv://user:pass@cluster.mongodb.net/crypto_news?retryWrites=true
```

❌ Invalid:
```
mongodb://localhost:27017/test
mongodb://localhost:27017/backdrop
mongodb://localhost:27017/  (no database specified)
```

## Related Tickets

- **FEATURE-014** - Investigation that discovered this issue
- **FEATURE-016** - Entity extraction validation (sibling from FEATURE-014)
- **FEATURE-017** - Actor salience threshold tuning (sibling from FEATURE-014)
- **FEATURE-018** - Post-clustering validation (sibling from FEATURE-014)

## Notes

This is a **defensive programming** measure that:
1. Prevents hours of debugging confusion
2. Makes failures obvious and immediate
3. Adds zero runtime overhead
4. Requires minimal code (~20 lines)

The investment of 15-30 minutes now saves hours of future debugging time.