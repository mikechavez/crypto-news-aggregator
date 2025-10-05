# Entity Normalization

## Overview

Entity normalization ensures consistent naming by mapping ticker variants to canonical names.

## Usage

### Normalize Entity Names

```python
from crypto_news_aggregator.services.entity_normalization import normalize_entity_name

canonical = normalize_entity_name("BTC")  # Returns "Bitcoin"
canonical = normalize_entity_name("$btc")  # Returns "Bitcoin"
canonical = normalize_entity_name("ethereum")  # Returns "Ethereum"
```

### Migration

```bash
# Dry run
python scripts/migrate_entity_normalization.py --dry-run

# Apply changes
python scripts/migrate_entity_normalization.py

# Recalculate signals
python scripts/recalculate_signals.py
```

## Testing

```bash
poetry run pytest tests/services/test_entity_normalization.py -v
```
