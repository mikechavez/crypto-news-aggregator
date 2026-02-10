# Entity Classification Migration Summary

## Problem
Entity mentions were using old classification types (`project`, `ticker`, `event`) which caused:
- Non-primary entities like "Pilot Program" and "Ai" appearing in signal scores
- Inconsistent entity classification across the system
- Difficulty filtering primary vs context entities

## Solution
Migrated all entities from old classification system to new system with proper `is_primary` flags.

### New Classification System
**Primary Entities** (appear in signals):
- `cryptocurrency`: Bitcoin, Ethereum, $BTC, $ETH
- `blockchain`: Ethereum, Solana, Avalanche
- `protocol`: Uniswap, 1Inch, Aave, Lido
- `company`: Coinbase, Circle, Anthropic, SpaceX

**Context Entities** (excluded from signals):
- `concept`: DeFi, Web3, Pilot Program, Ai
- `location`: New York, Abu Dhabi, Dubai
- `person`: Individual names
- `event`: Launches, upgrades, rallies

## Migration Process

### 1. Audit Script (`audit_entity_types.py`)
- Identified 295 entity mentions with old classification
- Found entities in signal_scores that needed reclassification

### 2. Migration Script (`migrate_old_entity_types.py`)
- Migrated 11 tickers → cryptocurrency (is_primary=True)
- Migrated 187 events → concept (is_primary=False)
- Migrated ~97 projects using smart rules:
  - Known concepts → concept (is_primary=False)
  - Known locations → location (is_primary=False)
  - Everything else → protocol (is_primary=True)

### 3. Signal Recalculation (`recalculate_signal_scores.py`)
- Deleted all existing signal scores (7 documents)
- Recalculated scores for 191 primary entities
- Only entities with `is_primary=True` are now scored

### 4. Verification (`verify_signal_cleanup.py`)
- ✅ Pilot Program NOT in signals
- ✅ Ai NOT in signals
- ✅ Web3 NOT in signals
- ✅ DeFi NOT in signals

## Results

### Signal Scores by Entity Type
- `company`: 63 entities
- `protocol`: 55 entities
- `cryptocurrency`: 50 entities
- `blockchain`: 23 entities

**Total**: 191 primary entities with signal scores

### Migration Statistics
- **Old classification**: 295 mentions
- **New classification**: 1,231 mentions
- **Remaining old types**: 0 (100% migrated)

## Scripts Created

1. **`scripts/audit_entity_types.py`**
   - Audits current state of entity classification
   - Identifies entities needing migration

2. **`scripts/migrate_old_entity_types.py`**
   - Performs bulk migration using rule-based mapping
   - Fast, deterministic classification

3. **`scripts/reclassify_old_types.py`**
   - Uses Claude Haiku for intelligent classification
   - Batch processing (50 entities at a time)
   - Useful for edge cases requiring AI judgment

4. **`scripts/verify_signal_cleanup.py`**
   - Verifies concept entities are excluded from signals
   - Shows distribution of entity types in signals

## Usage

```bash
# Audit current state
poetry run python scripts/audit_entity_types.py

# Migrate using rules (fast)
poetry run python scripts/migrate_old_entity_types.py

# Or reclassify using Claude (intelligent)
poetry run python scripts/reclassify_old_types.py

# Recalculate signal scores
poetry run python scripts/recalculate_signal_scores.py

# Verify results
poetry run python scripts/verify_signal_cleanup.py
```

## Impact

### Before Migration
- Signal scores included generic concepts
- "Pilot Program" had a signal score
- Inconsistent entity classification
- 295 entities with old types

### After Migration
- Only primary entities in signals
- Concept entities properly excluded
- Consistent classification system
- 0 entities with old types
- Clean signal scores for 191 primary entities

## Next Steps

1. Monitor signal scores in production
2. Verify UI displays clean entity list
3. Consider adding entity type filters to API endpoints
4. Document entity classification guidelines for future extractions
