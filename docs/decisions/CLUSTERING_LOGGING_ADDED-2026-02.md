# Clustering Logging Implementation

## Summary
Added comprehensive logging throughout the salience-based clustering pipeline to help debug and monitor narrative detection.

## Logging Added

### 1. `cluster_by_narrative_salience` Function

**Start of clustering**:
```
INFO: Starting clustering for {N} articles
```

**For each article**:
```
INFO: Article {idx}/{total}: {title[:50]}
INFO:   Nucleus: {nucleus}, Core actors: {core_actors}
INFO:   All actors: {actors}, Tensions: {tensions}
INFO:   Best cluster match: strength={best_strength:.2f}, threshold=0.8
```

**Match result**:
```
INFO:   ✓ Matched to existing cluster (now {N} articles)
  OR
INFO:   ✗ Created new cluster (total clusters: {N})
```

**End of clustering**:
```
INFO: Clustering complete: {N} total clusters, {M} substantial (>={min_size} articles)
INFO:   Cluster 1: {N} articles, nucleus={entity}
INFO:   Cluster 2: {N} articles, nucleus={entity}
...
```

### 2. `generate_narrative_from_cluster` Function

**Start of generation**:
```
INFO: Generating narrative for cluster of {N} articles
INFO:   Primary nucleus: {nucleus}
INFO:   Unique actors ({N}): {actors[:10]}
INFO:   Unique tensions ({N}): {tensions[:5]}
```

**End of generation**:
```
INFO:   Generated narrative: '{title}'
```

### 3. `merge_shallow_narratives` Function

**Start of merging**:
```
INFO: Starting shallow narrative merging for {N} narratives
```

**Classification**:
```
INFO: Shallow: '{title}' (articles={N}, actors={N}, nucleus={entity})
  OR
INFO: Substantial: '{title}' (articles={N}, actors={N}, nucleus={entity})
```

**Merge attempt**:
```
INFO: Attempting to merge {N} shallow narratives into {M} substantial ones
INFO: Merging shallow narrative: '{title}'
INFO:   Actors: {actors}
INFO:   Best match: similarity={score:.2f}, threshold=0.5
```

**Merge result**:
```
INFO:   ✓ Merged into '{target_title}'
  OR
INFO:   ✗ Kept as standalone (no good match)
```

**End of merging**:
```
INFO: Merge complete: {N} merged, {M} kept standalone, {total} total narratives
```

## Log Flow Example

```
INFO: Starting clustering for 15 articles
INFO: Article 1/15: SEC Charges Crypto Exchange for Securities Vio
INFO:   Nucleus: SEC, Core actors: ['SEC', 'Binance']
INFO:   All actors: ['SEC', 'Binance', 'Gary Gensler', 'DOJ'], Tensions: ['Regulation vs Innovation']
INFO:   Best cluster match: strength=0.00, threshold=0.8
INFO:   ✗ Created new cluster (total clusters: 1)

INFO: Article 2/15: Binance Faces Additional Regulatory Scrutiny
INFO:   Nucleus: Binance, Core actors: ['Binance', 'SEC']
INFO:   All actors: ['Binance', 'SEC', 'CFTC'], Tensions: ['Regulation vs Innovation', 'Compliance vs Growth']
INFO:   Best cluster match: strength=1.40, threshold=0.8
INFO:   ✓ Matched to existing cluster (now 2 articles)

...

INFO: Clustering complete: 5 total clusters, 3 substantial (>=3 articles)
INFO:   Cluster 1: 5 articles, nucleus=SEC
INFO:   Cluster 2: 4 articles, nucleus=Ethereum
INFO:   Cluster 3: 3 articles, nucleus=Bitcoin

INFO: Generating narrative for cluster of 5 articles
INFO:   Primary nucleus: SEC
INFO:   Unique actors (8): ['SEC', 'Binance', 'Coinbase', 'Gary Gensler', ...]
INFO:   Unique tensions (3): ['Regulation vs Innovation', 'Compliance vs Growth', ...]
INFO:   Generated narrative: 'SEC Intensifies Crypto Exchange Enforcement'

INFO: Starting shallow narrative merging for 5 narratives
INFO: Substantial: 'SEC Intensifies Crypto Exchange Enforcement' (articles=5, actors=8, nucleus=SEC)
INFO: Substantial: 'Ethereum Upgrade Drives DeFi Growth' (articles=4, actors=6, nucleus=Ethereum)
INFO: Shallow: 'Bitcoin Price Analysis' (articles=1, actors=2, nucleus=Bitcoin)

INFO: Attempting to merge 1 shallow narratives into 2 substantial ones
INFO: Merging shallow narrative: 'Bitcoin Price Analysis'
INFO:   Actors: ['Bitcoin', 'Traders']
INFO:   Best match: similarity=0.25, threshold=0.5
INFO:   ✗ Kept as standalone (no good match)

INFO: Merge complete: 0 merged, 1 kept standalone, 3 total narratives
```

## Benefits

1. **Debugging**: Trace exactly why articles cluster together or stay separate
2. **Threshold tuning**: See link strength scores to adjust clustering threshold
3. **Quality monitoring**: Identify weak narratives or over-clustering
4. **Performance tracking**: Monitor cluster sizes and merge rates
5. **Transparency**: Understand narrative detection decisions

## Log Levels

- **INFO**: Normal operation flow, clustering decisions, results
- **WARNING**: JSON parsing failures, empty responses (already in code)
- **EXCEPTION**: Errors during generation or clustering (already in code)

## Configuration

Logging is controlled by the standard Python logging configuration. To see detailed clustering logs:

```python
import logging
logging.getLogger('crypto_news_aggregator.services.narrative_themes').setLevel(logging.INFO)
```

Or in production, configure via logging config file to route to appropriate handlers.
