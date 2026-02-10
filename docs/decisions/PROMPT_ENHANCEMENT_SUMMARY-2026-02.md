# Narrative Extraction Prompt Enhancement

**Date:** October 12, 2025  
**Status:** ✅ Complete

## Overview
Enhanced the LLM prompt in `discover_narrative_from_article()` to improve entity normalization and nucleus selection quality.

## Changes Made

### File Modified
- `src/crypto_news_aggregator/services/narrative_themes.py` (lines 371-401)

### Enhancement Details

Added **ENTITY NORMALIZATION GUIDELINES** section to the prompt with three key components:

#### 1. Entity Name Normalization Rules
Provides specific examples of how to normalize common entity variations:
- SEC variations → "SEC"
- Ethereum variations → "Ethereum"
- Tether variations → "Tether"
- Bitcoin variations → "Bitcoin"
- Binance variations → "Binance"

**Key principles:**
- Use shortest, most recognizable form
- Use common abbreviations (SEC, ETF, DeFi)
- For cryptocurrencies, use name not ticker (Bitcoin not BTC)

#### 2. Nucleus Entity Selection Rules
Clear guidelines for choosing the primary entity:
- Choose entity most directly responsible for main action
- Prefer specific entities over generic categories
- Prefer actors over objects in regulatory stories
- Prefer companies/organizations over people (unless person is the focus)
- Nucleus should be grammatical subject of article's main action

#### 3. Salience Scoring Consistency
Stricter guidelines to prevent over-scoring:
- Reserve salience 5 for 1-2 entities maximum (true protagonists)
- Use salience 4 for 2-4 key participants
- Use salience 3 for 3-6 secondary participants
- Be selective - avoid giving everything high salience
- Exclude background mentions (salience 1)

## Expected Impact

### Improved Entity Normalization
- **Reduces duplicates**: "SEC" vs "U.S. SEC" vs "Securities and Exchange Commission"
- **Better clustering**: Similar articles will use same entity names
- **Cleaner entity graphs**: Fewer fragmented entity nodes

### Better Nucleus Selection
- **More consistent**: Clear rules for edge cases
- **More meaningful**: Focus on actors not abstract concepts
- **Better narrative linking**: Articles about same entity will cluster properly

### More Accurate Salience Scores
- **Less inflation**: Prevents everything being scored 4-5
- **Better differentiation**: Clear tiers of importance
- **Improved filtering**: Salience >= 2 threshold becomes more meaningful

## Testing Recommendations

1. **Run on recent articles** to see immediate impact:
   ```bash
   # Test on last 50 articles
   poetry run python scripts/test_narrative_extraction.py --limit 50
   ```

2. **Compare entity distributions** before/after:
   - Check for reduction in entity variants
   - Verify nucleus entity consistency
   - Analyze salience score distributions

3. **Monitor clustering quality**:
   - Check if similar articles cluster better
   - Verify narrative themes are more coherent
   - Look for reduction in single-article narratives

## Cache Invalidation

⚠️ **Important**: This prompt change will affect the content hash calculation.

- Existing cached narratives will remain valid
- New extractions will use enhanced prompt
- Gradual improvement as cache refreshes naturally
- Consider manual cache clear if immediate full reprocessing is needed

## Next Steps

1. ✅ Prompt enhancement complete
2. ⏳ Test on sample articles
3. ⏳ Monitor entity normalization quality
4. ⏳ Evaluate clustering improvements
5. ⏳ Consider additional normalization rules based on results

## Related Files
- Implementation: `src/crypto_news_aggregator/services/narrative_themes.py`
- Validation: `src/crypto_news_aggregator/services/narrative_validation.py`
- Caching: `NARRATIVE_CACHING_IMPLEMENTATION.md`
- Test Results: `NARRATIVE_CACHING_TEST_RESULTS.md`
