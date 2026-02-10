# Narrative Inspection Results

**Date:** October 12, 2025  
**Script:** `scripts/inspect_narratives.py`

## Summary

✅ **Database is in good shape** - 81% of narratives are already using the new entity-based system.

## Key Findings

### Overall Statistics
- **Total narratives:** 27
- **Theme-based (old system):** 5 (19%)
- **Entity-based (new system):** 22 (81%)
- **Age:** All narratives are 0 days old (recently created/updated)

### Narrative Quality Assessment

The database contains a healthy mix of narratives across different lifecycle stages:

#### Mature Narratives (High Article Count)
1. **Crypto Market Volatility: Analyzing the Crash and Recovery** - 51 articles
2. **Crypto Regulatory Woes: Crashes, Probes, and Outrage** - 44 articles
3. **Institutional Investment in Crypto Amid Market Volatility** - 31 articles
4. **Crypto Security Challenges** - 28 articles
5. **Crypto firms expand infrastructure and investment** - 11 articles

#### Hot/Emerging Narratives
- **Defi Adoption Narrative** - 10 articles (hot)
- **Stablecoins Face Turbulence** - 7 articles (hot)
- **Crypto Payments** - 2 articles (emerging)
- **Arbitrum Hires New Head, Sorare Moves to Solana L1** - 2 articles (emerging)
- **NFT Gaming Platforms Migrate and Expand** - 2 articles (emerging)

### Theme-Based vs Entity-Based

**Theme-based narratives (5):**
- Regulatory
- Payments
- Security
- Infrastructure
- (These use generic themes)

**Entity-based narratives (22):**
- Focus on specific entities like: Donald Trump, Tether, Coinbase, Solana, Arbitrum
- More specific and actionable
- Better for signal detection

## Recommendation

✅ **KEEP EXISTING NARRATIVES**

**Rationale:**
1. 81% are already using the new entity-based system
2. All narratives are fresh (0 days old)
3. Good distribution across lifecycle stages
4. High-quality mature narratives with substantial article counts
5. New narratives from backfill will merge naturally with existing ones

**Action Items:**
1. ✅ Continue with backfill process
2. ✅ Let narrative discovery run naturally
3. ✅ Monitor for duplicate narratives (deduplication system should handle this)
4. ❌ **DO NOT** clear narratives - they're already high quality

## Sample Narratives

### Example 1: Entity-Based (New System)
```
Title: Institutional Investment in Crypto Amid Market Volatility
Theme: institutional_investment
Type: Entity-based
Articles: 31
Entities: stablecoin, AI data center, Tether, Donald Trump Jr., Coinbase
Lifecycle: mature
```

### Example 2: Theme-Based (Old System)
```
Title: Crypto Regulatory Woes: Crashes, Probes, and Outrage
Theme: regulatory
Type: Theme-based
Articles: 44
Entities: FTX, stablecoin, Bitget, Donald Trump Jr., Crypto.com
Lifecycle: mature
```

## Next Steps

1. **Continue backfill:** Process remaining articles to extract entities and sentiment
2. **Monitor narrative growth:** Watch for new narratives emerging from backfilled data
3. **Verify deduplication:** Ensure similar narratives are being merged correctly
4. **Signal generation:** Once backfill completes, verify signal scores are calculated correctly

## Script Usage

To inspect narratives at any time:
```bash
poetry run python scripts/inspect_narratives.py
```

The script will:
- Count total narratives
- Show sample narratives with details
- Analyze theme-based vs entity-based distribution
- Provide recommendations based on the data
