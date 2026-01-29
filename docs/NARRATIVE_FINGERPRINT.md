# Narrative Fingerprint Field

## Overview

The narrative fingerprint is a composite data structure that captures the essential structural components of a narrative cluster. It enables intelligent matching, deduplication, and similarity analysis between narratives without requiring semantic embeddings.

## Purpose

The fingerprint serves as a lightweight, deterministic representation of a narrative that can be used to:

1. **Match similar narratives** across time periods
2. **Detect narrative evolution** by comparing fingerprints
3. **Deduplicate narratives** that represent the same story
4. **Enable fast similarity checks** without expensive LLM calls

## Structure

A narrative fingerprint contains four key components:

```python
{
    "nucleus_entity": str,        # The central protagonist of the narrative
    "top_actors": List[str],      # Top 5 actors sorted by salience (descending)
    "key_actions": List[str],     # Top 3 actions/events
    "timestamp": datetime          # When the fingerprint was computed
}
```

### Components

#### 1. Nucleus Entity
- **Type**: `string`
- **Description**: The primary entity the narrative is about
- **Example**: `"SEC"`, `"Ethereum"`, `"Bitcoin"`
- **Purpose**: Strongest signal for narrative matching (same nucleus = likely same story)

#### 2. Top Actors
- **Type**: `List[str]` (max 5 items)
- **Description**: Key participants sorted by salience score (highest to lowest)
- **Example**: `["SEC", "Binance", "Coinbase", "Kraken", "Gemini"]`
- **Purpose**: Secondary matching signal (shared high-salience actors indicate related narratives)

#### 3. Key Actions
- **Type**: `List[str]` (max 3 items)
- **Description**: Main events or actions in the narrative
- **Example**: `["Filed lawsuit", "Announced framework", "Issued enforcement"]`
- **Purpose**: Contextual signal for narrative evolution tracking

#### 4. Timestamp
- **Type**: `datetime` (UTC)
- **Description**: When the fingerprint was computed
- **Purpose**: Track narrative freshness and evolution over time

## Usage

### Basic Usage

```python
from crypto_news_aggregator.services.narrative_themes import compute_narrative_fingerprint

# Create a cluster dict with narrative data
cluster = {
    "nucleus_entity": "SEC",
    "actors": {
        "SEC": 5,
        "Binance": 4,
        "Coinbase": 4,
        "Kraken": 3
    },
    "actions": [
        "Filed lawsuit against exchanges",
        "Announced regulatory framework",
        "Issued enforcement actions"
    ]
}

# Compute fingerprint
fingerprint = compute_narrative_fingerprint(cluster)

print(fingerprint)
# {
#     "nucleus_entity": "SEC",
#     "top_actors": ["SEC", "Binance", "Coinbase", "Kraken"],
#     "key_actions": ["Filed lawsuit...", "Announced...", "Issued..."],
#     "timestamp": datetime(2025, 10, 15, 17, 48, 17, tzinfo=timezone.utc)
# }
```

### Input Formats

The function accepts two formats for the `actors` field:

#### Format 1: Dict with Salience Scores (Recommended)
```python
cluster = {
    "nucleus_entity": "Ethereum",
    "actors": {
        "Ethereum": 5,
        "Vitalik Buterin": 4,
        "EIP-4844": 3
    },
    "actions": ["Deployed upgrade"]
}
```

#### Format 2: List of Actors
```python
cluster = {
    "nucleus_entity": "Ethereum",
    "actors": ["Ethereum", "Vitalik Buterin", "EIP-4844"],
    "actions": ["Deployed upgrade"]
}
```

## Matching Logic

### Similarity Calculation

Use fingerprints to calculate narrative similarity:

```python
def calculate_similarity(fp1, fp2):
    """Calculate similarity between two fingerprints."""
    
    # Strongest signal: Same nucleus entity
    same_nucleus = fp1['nucleus_entity'] == fp2['nucleus_entity']
    
    # Medium signal: Shared actors
    shared_actors = set(fp1['top_actors']) & set(fp2['top_actors'])
    actor_overlap = len(shared_actors) / max(len(fp1['top_actors']), len(fp2['top_actors']))
    
    # Weak signal: Shared actions
    shared_actions = set(fp1['key_actions']) & set(fp2['key_actions'])
    action_overlap = len(shared_actions) / max(len(fp1['key_actions']), len(fp2['key_actions']))
    
    # Weighted similarity score
    if same_nucleus:
        similarity = 1.0 + (actor_overlap * 0.7) + (action_overlap * 0.3)
    else:
        similarity = (actor_overlap * 0.7) + (action_overlap * 0.3)
    
    return similarity
```

### Matching Thresholds

Recommended thresholds for narrative matching:

- **High confidence match** (similarity >= 1.5): Same nucleus + significant actor overlap
- **Medium confidence match** (similarity >= 0.8): Same nucleus OR strong actor overlap
- **Low confidence match** (similarity >= 0.5): Moderate actor/action overlap
- **No match** (similarity < 0.5): Different narratives

## Implementation Details

### Actor Sorting

When actors are provided as a dict with salience scores, they are sorted in descending order:

```python
sorted_actors = sorted(
    actors_dict.items(),
    key=lambda x: x[1],  # Sort by salience score
    reverse=True         # Highest first
)
top_actors = [actor for actor, _ in sorted_actors[:5]]
```

### Limits

- **Top actors**: Limited to 5 (prevents bloat, focuses on key players)
- **Key actions**: Limited to 3 (captures main events without noise)

### Edge Cases

The function handles edge cases gracefully:

- **Empty cluster**: Returns empty strings/lists with current timestamp
- **Missing fields**: Returns empty values for missing components
- **Fewer than limits**: Returns all available items (e.g., 2 actors if only 2 exist)

## Future Enhancements

### Phase 2: Semantic Embeddings (Not Yet Implemented)

Future versions may include semantic embeddings for more sophisticated matching:

```python
fingerprint = {
    "nucleus_entity": "SEC",
    "top_actors": ["SEC", "Binance"],
    "key_actions": ["Filed lawsuit"],
    "timestamp": datetime.now(timezone.utc),
    "embedding": [0.123, 0.456, ...]  # 768-dim vector from sentence transformer
}
```

This would enable:
- Fuzzy matching of similar but not identical narratives
- Cross-lingual narrative matching
- Semantic clustering without exact entity matches

## Testing

Comprehensive tests are available in `tests/services/test_narrative_themes.py`:

```bash
poetry run pytest tests/services/test_narrative_themes.py::TestComputeNarrativeFingerprint -v
```

Test coverage includes:
- Dict and list actor formats
- Empty and partial clusters
- Actor/action limits
- Salience-based sorting
- Timestamp validation

## Examples

See `examples/narrative_fingerprint_example.py` for complete usage examples:

```bash
poetry run python examples/narrative_fingerprint_example.py
```

## Related Functions

- `discover_narrative_from_article()`: Extracts narrative data from articles
- `cluster_by_narrative_salience()`: Groups articles into narrative clusters
- `generate_narrative_from_cluster()`: Creates narrative summaries from clusters
- `validate_narrative_json()`: Validates narrative data structure

## References

- Main implementation: `src/crypto_news_aggregator/services/narrative_themes.py`
- Tests: `tests/services/test_narrative_themes.py`
- Examples: `examples/narrative_fingerprint_example.py`
