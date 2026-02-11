# Organization Entity Type Implementation

## Summary

Added **"organization"** as a new primary entity type for tracking government agencies, regulatory bodies, and non-profit organizations in crypto news.

## Changes Made

### 1. Updated EntityType Enum (`src/crypto_news_aggregator/db/models.py`)

**Added:**
```python
ORGANIZATION = "organization"  # Government agencies, NGOs, regulatory bodies
```

**Updated `is_primary()` method:**
```python
primary_types = {
    cls.CRYPTOCURRENCY,
    cls.PROTOCOL,
    cls.COMPANY,
    cls.BLOCKCHAIN,
    cls.ORGANIZATION,  # Now included
}
```

### 2. Updated Entity Extraction Prompt (`src/crypto_news_aggregator/llm/anthropic.py`)

**Added to PRIMARY entities:**
```
- organization: SEC, Federal Reserve, IMF, World Bank, CFTC (government/regulatory/NGO)
```

This helps the LLM correctly classify regulatory and government entities.

### 3. Reclassified Existing Entities

**Script:** `scripts/reclassify_organizations.py`

**Reclassified entities:**
- SEC (2 mentions)
- Standard Chartered (3 mentions)
- European Central Bank (2 mentions)
- Morgan Stanley, JPMorgan, SBI, IRS (1 each)

**Total:** 11 mentions reclassified from `company` → `organization`

## Current State

### Primary Entity Type Distribution:
```
cryptocurrency:  713 mentions
company:         181 mentions
blockchain:      122 mentions
protocol:        116 mentions
organization:     11 mentions  ← NEW
```

### Organization Entities with Signal Scores:
```
Entity                    Velocity  Sources  Score
Standard Chartered        24.00     1        9.98
SEC                       24.00     1        9.98
JPMorgan                  24.00     0        9.90
Morgan Stanley            0.00      1        7.58
SBI                       0.00      1        7.58
IRS                       24.00     0        2.40
European Central Bank     0.00      1        0.07
```

## Why This Matters

### Better Entity Classification:
- **Before:** SEC, Federal Reserve, etc. were classified as "company"
- **After:** Properly classified as "organization" (government/regulatory)

### Improved Signal Detection:
- Organizations have different impact patterns than companies
- Regulatory announcements (SEC, CFTC) are high-signal events
- Central bank actions (Federal Reserve, ECB) affect markets differently

### Future Analytics:
- Track regulatory activity separately from corporate activity
- Identify when government/regulatory entities are trending
- Correlate regulatory mentions with market movements

## Examples of Organizations

### Government/Regulatory:
- SEC (Securities and Exchange Commission)
- CFTC (Commodity Futures Trading Commission)
- FinCEN (Financial Crimes Enforcement Network)
- Federal Reserve
- European Central Bank
- Bank of England

### International Bodies:
- IMF (International Monetary Fund)
- World Bank
- G20
- United Nations
- OECD
- Basel Committee

### Financial Institutions (Regulatory Role):
- Standard Chartered
- JPMorgan (when acting in regulatory/policy context)
- Morgan Stanley (when acting in regulatory/policy context)

## Testing

### Verify Organization Classification:
```bash
poetry run python scripts/check_organization_entities.py
```

### Reclassify More Entities:
```bash
poetry run python scripts/reclassify_organizations.py
```

### Recalculate Signals:
```bash
poetry run python scripts/recalculate_all_signals.py
```

## Next Steps

### Immediate:
- ✅ Entity type added to enum
- ✅ LLM prompt updated
- ✅ Existing entities reclassified
- ✅ Signal scores recalculated

### Future Enhancements:
1. **Add more organizations** to reclassification script as they appear
2. **Create organization-specific alerts** (e.g., "SEC mentioned 5+ times in hour")
3. **Track regulatory sentiment** separately from market sentiment
4. **Correlate organization mentions** with price movements

## Deployment

### Files to Deploy:
```
src/crypto_news_aggregator/db/models.py
src/crypto_news_aggregator/llm/anthropic.py
scripts/reclassify_organizations.py
scripts/check_organization_entities.py
```

### Post-Deployment:
1. Run reclassification script on production database
2. Recalculate all signal scores
3. Monitor for new organization entities in future articles

## Impact on Signal Scores

Organizations now tracked as primary entities means:
- **Velocity** calculated for regulatory activity
- **Source diversity** shows which outlets cover regulatory news
- **Signal scores** reflect importance of regulatory announcements

Example: SEC approval of Bitcoin ETF would show:
- High velocity (many mentions in short time)
- High source diversity (all outlets covering it)
- High signal score (trending regulatory event)

## Related Documentation

- `SIGNAL_CALCULATION_FIX.md` - Signal calculation fixes
- `ACTION_ITEMS_SUMMARY.md` - Deployment checklist
- `src/crypto_news_aggregator/db/models.py` - EntityType enum
