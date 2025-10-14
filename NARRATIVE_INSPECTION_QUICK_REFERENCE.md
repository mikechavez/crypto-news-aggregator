# Narrative Inspection Quick Reference

## TL;DR

✅ **Your narratives are in excellent shape!**
- 27 total narratives
- 81% are entity-based (new system)
- 19% are theme-based (old system)
- All are fresh (0 days old)
- **Recommendation: Keep them, don't clear**

## Quick Command

```bash
poetry run python scripts/inspect_narratives.py
```

## What the Script Does

1. **Counts narratives** - Total in database
2. **Shows samples** - First 10 narratives with details
3. **Analyzes types** - Theme-based vs Entity-based
4. **Provides recommendation** - Clear or keep

## Understanding the Output

### Narrative Types

**Theme-based (Old System):**
- Uses generic themes: `regulatory`, `defi`, `security`, `payments`
- Less specific
- Example: "Crypto Regulatory Woes"

**Entity-based (New System):**
- Uses specific entities: `Tether`, `Coinbase`, `Solana`
- More actionable
- Better for signals
- Example: "Institutional Investment in Crypto Amid Market Volatility"

### Lifecycle Stages

- **emerging** - New narrative, 2-5 articles
- **hot** - Growing rapidly, 6-15 articles
- **mature** - Established, 15+ articles
- **declining** - Losing momentum

## Current State (Oct 12, 2025)

### Top Narratives by Article Count

1. **Crypto Market Volatility** - 51 articles (mature)
2. **Crypto Regulatory Woes** - 44 articles (mature)
3. **Institutional Investment** - 31 articles (mature)
4. **Crypto Security Challenges** - 28 articles (mature)
5. **Infrastructure Expansion** - 11 articles (mature)

### Distribution

```
Total: 27 narratives
├── Theme-based: 5 (19%)
│   ├── Regulatory
│   ├── Payments
│   ├── Security
│   ├── Infrastructure
│   └── (1 more)
└── Entity-based: 22 (81%)
    ├── Institutional Investment
    ├── Market Analysis
    ├── Defi Adoption
    ├── Stablecoin
    └── (18 more)
```

## When to Clear Narratives

❌ **Don't clear if:**
- Most narratives are entity-based (like now - 81%)
- Narratives are fresh and high quality
- Good distribution across lifecycle stages

⚠️ **Consider clearing if:**
- Most narratives are theme-based (>60%)
- Narratives are stale (>30 days old)
- Low article counts across the board
- After major system changes

## Next Steps

1. ✅ Continue backfill process
2. ✅ Monitor narrative growth
3. ✅ Let deduplication system merge similar narratives
4. ✅ Verify signal scores after backfill completes

## Related Scripts

- `scripts/inspect_narratives.py` - This inspection script
- `scripts/clean_narratives.py` - Clear narratives (use with caution!)
- `scripts/backfill_narratives.py` - Backfill article data

## Related Docs

- `NARRATIVE_INSPECTION_RESULTS.md` - Detailed inspection results
- `NARRATIVE_CACHING_IMPLEMENTATION.md` - Narrative system architecture
- `NARRATIVE_DISCOVERY_IMPLEMENTATION.md` - How narratives are discovered
