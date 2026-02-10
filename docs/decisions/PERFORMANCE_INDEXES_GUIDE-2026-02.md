# Performance Indexes Guide

## Overview

The `scripts/add_performance_indexes.py` script creates optimized MongoDB indexes for frequently queried collections in the crypto news aggregator application.

## Created Indexes

### Articles Collection
- **idx_published_at_desc_perf**: Descending index on `published_at`
  - Optimizes time-based queries and sorting by publication date
  - Used for: Recent articles, timeline queries
  
- **idx_entities_asc**: Ascending index on `entities`
  - Optimizes entity-based article lookups
  - Used for: Finding articles mentioning specific entities

### Entity Mentions Collection
- **idx_entity_created_at_desc_perf**: Compound index on `entity` (asc) + `created_at` (desc)
  - Optimizes entity timeline queries and velocity calculations
  - Used for: Tracking entity mentions over time, calculating mention velocity
  
- **idx_entity_source_compound**: Compound index on `entity` (asc) + `source` (asc)
  - Optimizes source diversity calculations for entities
  - Used for: Counting unique sources mentioning an entity

### Signal Scores Collection
- **idx_score_24h_desc**: Descending index on `score_24h`
  - Optimizes 24-hour timeframe signal queries and sorting
  
- **idx_score_7d_desc**: Descending index on `score_7d`
  - Optimizes 7-day timeframe signal queries and sorting
  
- **idx_score_30d_desc**: Descending index on `score_30d`
  - Optimizes 30-day timeframe signal queries and sorting

### Narratives Collection
- **idx_lifecycle_state_last_updated_desc**: Compound index on `lifecycle_state` (asc) + `last_updated` (desc)
  - Optimizes lifecycle-based narrative queries and sorting
  - Used for: Filtering narratives by lifecycle state (emerging, hot, cooling, etc.)

## Usage

Run the script to create all indexes:

```bash
poetry run python scripts/add_performance_indexes.py
```

## Features

- **Idempotent**: Safe to run multiple times - skips existing indexes
- **Background Creation**: All indexes are created in the background to avoid blocking
- **Comprehensive Logging**: Detailed output showing index creation progress
- **Error Handling**: Graceful error handling with detailed error messages

## Performance Impact

These indexes significantly improve query performance for:
- ✓ Time-based article queries
- ✓ Entity mention lookups and velocity calculations
- ✓ Signal score sorting across timeframes
- ✓ Narrative lifecycle filtering and sorting

## Notes

- All indexes are created with `background=True` to minimize impact on running services
- The script uses async/await with motor for efficient MongoDB operations
- Existing indexes are detected and skipped automatically
- The script properly closes MongoDB connections on completion
