# Theme-Based vs Entity-Based Narrative Analysis

## Summary

**Total Narratives:** 227
- **Theme-Based:** 15 (6.6%)
- **Entity-Based:** 212 (93.4%)

## Categorization Logic

A narrative is classified as **theme-based** if its `nucleus_entity` (from `fingerprint.nucleus_entity` or `theme` field):

1. **Contains underscores** - indicating compound themes (e.g., `nft_gaming`, `layer2_scaling`, `defi_adoption`)
2. **Is a generic lowercase term** - without proper capitalization (e.g., `regulatory`, `payments`, `security`, `infrastructure`, `stablecoin`, `technology`, `partnerships`, `institutional_investment`, `market_analysis`)

Entity-based narratives have proper capitalization indicating specific entities (e.g., `Bitcoin`, `Ethereum`, `Solana`, `SEC`, `Coinbase`).

## Theme-Based Narratives (15 total)

### Complete List:
1. **defi_adoption** - 1 narrative (10 articles, cooling)
2. **institutional_investment** - 1 narrative (31 articles, cooling)
3. **payments** - 1 narrative (2 articles, cooling)
4. **layer2_scaling** - 1 narrative (2 articles, cooling)
5. **security** - 1 narrative (28 articles, cooling)
6. **infrastructure** - 1 narrative (11 articles, cooling)
7. **nft_gaming** - 1 narrative (2 articles, cooling)
8. **stablecoin** - 1 narrative (7 articles, cooling)
9. **market_analysis** - 1 narrative (51 articles, cooling)
10. **technology** - 1 narrative (12 articles, cooling)
11. **partnerships** - 1 narrative (cooling)
12. **crypto market** - 1 narrative (cooling)
13. **crypto traders** - 1 narrative (cooling)
14. **Tokenization** - 1 narrative (hot) - Note: Has proper capitalization but still theme-based
15. **regulatory** - 1 narrative (cooling)

### State Distribution:
- **cooling:** 14 narratives
- **hot:** 1 narrative

### Example Theme-Based Narratives:

**1. institutional_investment**
- Title: "Institutional Investment in Crypto Amid Market Volatility"
- Articles: 31
- State: cooling
- Summary: Explores impact of crypto market downturn on institutional investment

**2. layer2_scaling**
- Title: "Arbitrum Hires New Head, Sorare Moves to Solana L1"
- Articles: 2
- State: cooling
- Summary: Arbitrum Foundation hiring and Sorare's migration to Solana

**3. nft_gaming**
- Title: "NFT Gaming Platforms Migrate and Expand"
- Articles: 2
- State: cooling
- Summary: NFT gaming platform developments

## Entity-Based Narratives (212 total)

### Top 20 Entity Distribution:
1. **Bitcoin** - 25 narratives
2. **Ethereum** - 8 narratives
3. **Ripple** - 7 narratives
4. **SEC** - 6 narratives
5. **Crypto** - 5 narratives
6. **XRP** - 5 narratives
7. **Coinbase** - 5 narratives
8. **Tether** - 4 narratives
9. **BNB** - 4 narratives
10. **Gold** - 4 narratives
11. **BlackRock** - 4 narratives
12. **Binance** - 4 narratives
13. **Solana** - 3 narratives
14. **WazirX** - 3 narratives
15. **Shiba Inu** - 3 narratives
16. **Benzinga** - 3 narratives
17. **HBAR** - 3 narratives
18. **Crypto market** - 3 narratives
19. **Hyperliquid** - 3 narratives
20. **Erebor** - 3 narratives

### State Distribution:
- **hot:** 121 narratives
- **emerging:** 66 narratives
- **rising:** 13 narratives
- **cooling:** 10 narratives
- **dormant:** 2 narratives

### Example Entity-Based Narratives:

**1. Bitcoin**
- 25 narratives total
- Various states (hot, emerging, cooling)
- Focus on specific Bitcoin-related events and price movements

**2. Ethereum**
- 8 narratives total
- Primarily emerging state
- Focus on Ethereum-specific developments

## Backfill Scope

### Narratives Requiring Theme-Based Fingerprint Generation:
**15 narratives** need to have their fingerprints regenerated using theme-based logic.

These narratives currently have fingerprints generated with entity-based logic (focusing on specific actors and actions), but should instead use theme-based logic that:
- Identifies broader thematic patterns
- Focuses on concepts and trends rather than specific entities
- Captures cross-entity themes and narratives

### Narratives with Correct Entity-Based Fingerprints:
**212 narratives** already have appropriate entity-based fingerprints and require no changes.

## Key Observations

1. **Small Theme-Based Population**: Only 6.6% of narratives are theme-based, suggesting most narratives focus on specific entities rather than broader themes.

2. **Theme-Based Narratives are Cooling**: 14 of 15 theme-based narratives are in "cooling" state, suggesting they may be older or less actively discussed.

3. **Entity-Based Narratives are Active**: The majority of entity-based narratives are in "hot" (121) or "emerging" (66) states, indicating active discussion.

4. **Bitcoin Dominance**: Bitcoin has the most entity-based narratives (25), followed by Ethereum (8) and Ripple (7).

5. **Compound Themes**: Theme-based narratives with underscores (`layer2_scaling`, `nft_gaming`, `defi_adoption`) clearly indicate multi-concept themes.

6. **Generic Terms**: Single-word lowercase themes (`payments`, `security`, `infrastructure`, `regulatory`) represent broad industry concepts rather than specific entities.

## Next Steps

1. ✅ **Confirm categorization logic** - Review the 15 theme-based examples to ensure categorization is accurate
2. **Run backfill script** - Generate theme-based fingerprints for the 15 identified narratives
3. **Verify fingerprint quality** - Check that new fingerprints properly capture thematic patterns
4. **Monitor impact** - Track how theme-based fingerprints affect narrative matching and clustering

## Script Location

The analysis script is located at:
```
scripts/count_theme_vs_entity_narratives.py
```

Run with:
```bash
poetry run python scripts/count_theme_vs_entity_narratives.py
```
