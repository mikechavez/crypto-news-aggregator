# Narrative Quality Audit - Quick Start

## Overview

The `scripts/audit_narrative_quality.py` script performs comprehensive data quality analysis on all narratives in the database.

## Features

### Part 1: Audit Metadata
- Total narratives and articles
- Median/average article counts
- Median age of narratives
- Top 5 entities by narrative count
- % narratives with complete data

### Part 2: Issue Categories

**A. Generic/Vague Narratives**
- Detects generic entities (BTC, ETH, crypto, etc.)
- Identifies generic title keywords (Activity, Updates, News, etc.)
- Flags generic summary phrases
- **Double penalty** for narratives with BOTH generic title AND summary

**B. Low Article Count (Time-Aware)**
- **Emerging**: created < 3d AND article_count < 3 → MONITOR
- **Failed**: created > 7d AND article_count < 3 → DELETE
- **Stalled**: created > 14d AND article_count < 5 → MERGE or DELETE

**C. Stale Narratives + Lifecycle Mismatch**
- Buckets: 7-14d, 14-30d, 30d+
- **Mismatch detection**: lifecycle_state ∈ ['hot', 'emerging'] BUT last_updated > 7d

**D. Duplicate/Similar Titles**
- **Exact duplicates**: normalized lowercase matching
- **Fuzzy duplicates**: SequenceMatcher ratio > 0.85 (first 100 narratives)
- **Fingerprint duplicates**: fingerprint similarity >= 0.8 (first 100 narratives)

**E. Missing/Incomplete Data**
- Missing title, summary, entities, fingerprint
- **Zero article bug**: article_count = 0 BUT lifecycle_state != dormant

**F. Old Schema Narratives**
- Has nucleus_entity but no title
- Has actors dict but no entities array
- Has narrative_summary but no summary

### Part 3: Quality Scoring (0-110)

Score calculation per narrative:
```
score = 100
  - 20 if generic/vague (40 if BOTH title AND summary generic)
  - 20 if failed/stalled low count
  - 20 if stale
  - 20 if missing critical data
  - 20 if duplicate
  + 10 if high-performer (article_count >= 10 AND lifecycle ∈ ['hot', 'rising'])
```

**Score Distribution:**
- 90-110 (excellent/anchor)
- 70-89 (good)
- 50-69 (fair)
- 30-49 (poor)
- 0-29 (bad)

**Top 5 Offenders**: Shows lowest scoring narratives with issue breakdown

### Part 4: Cleanup Recommendations

Provides actionable recommendations with:
- Category
- Action (DELETE, MERGE, UPDATE STATE, BACKFILL)
- Confidence level (HIGH, MEDIUM, LOW)
- Count of affected narratives
- Priority (HIGH, MEDIUM, LOW)

## Usage

```bash
poetry run python scripts/audit_narrative_quality.py
```

## Output Files

1. **NARRATIVE_QUALITY_AUDIT.md** - Human-readable markdown report
2. **NARRATIVE_QUALITY_AUDIT.json** - Structured JSON data with:
   - `metadata`: Overview statistics
   - `issues`: Detailed issue categorization
   - `scores`: Per-narrative quality scores
   - `recommendations`: Cleanup actions

## Example Output

```
🔍 Starting Narrative Quality Audit...
================================================================================
PART 1: AUDIT METADATA
================================================================================

📊 Overview:
  Total narratives: 133
  Total articles: 876
  Median article count: 4
  Average articles: 6.59
  Median age: 2 days

🏆 Top 5 entities:
    Unknown: 125
    Jack Dorsey: 1
    ...

✅ Complete data: 125 (94.0%)

================================================================================
PART 2: ISSUE CATEGORIES
================================================================================

🔤 A. Generic/Vague: 11 (8.3%)
  Total articles: 33
  Double penalty: 0
  ...

📉 B. Low Article Count:
  EMERGING: 8
  FAILED: 0
  STALLED: 0
  ...

⏰ C. Stale Narratives:
  7-14d: 0
  14-30d: 0
  30d+: 0
  ⚠️  Lifecycle mismatches: 0

🔄 D. Duplicates:
  Exact: 12 groups, 24 narratives
  ...

❌ E. Missing Data:
  title: 8 (6.0%)
  summary: 8 (6.0%)
  ...

🏛️  F. Old Schema: 24 total
  ...

================================================================================
PART 3: QUALITY SCORING (0-110)
================================================================================

📊 Score Distribution:
  90-110: 104
  70-89: 21
  50-69: 8
  30-49: 0
  0-29: 0

⚠️  TOP 5 OFFENDERS:
  1. Score: 60/110
     Title: ...
     Issues: generic, missing_data
  ...

================================================================================
PART 4: CLEANUP RECOMMENDATIONS
================================================================================

| Category | Action | Confidence | Count | Priority |
|----------|--------|-----------|-------|----------|
| Generic | DELETE | HIGH | 11 | MEDIUM |
| Duplicates | MERGE | MEDIUM | 24 | HIGH |
```

## Implementation Details

### Files
- `scripts/audit_narrative_quality.py` - Main script
- `scripts/audit_analysis.py` - Analysis module with all logic

### Dependencies
- `src.crypto_news_aggregator.db.mongodb.mongo_manager` - Database access
- `src.crypto_news_aggregator.services.narrative_themes.calculate_fingerprint_similarity` - Fingerprint comparison
- `difflib.SequenceMatcher` - Title fuzzy matching

### Key Functions
- `parse_datetime()` - Timezone-aware datetime parsing
- `run_full_audit()` - Main audit orchestration
- `write_markdown_report()` - Generate MD report
- `write_json_report()` - Generate JSON report

## Next Steps

After running the audit:

1. **Review the reports** to understand data quality issues
2. **Prioritize cleanup** based on recommendations table
3. **Run cleanup scripts** for high-priority issues:
   - Delete generic narratives
   - Merge duplicates
   - Update lifecycle mismatches
   - Backfill missing data
4. **Re-run audit** to verify improvements

## Notes

- Script is safe to run multiple times
- No database modifications are made (read-only)
- Performance: Fuzzy/fingerprint duplicate detection limited to first 100 narratives to avoid O(n²) explosion
- Timezone-aware datetime handling for accurate age calculations
