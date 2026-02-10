# Missing Narratives Processing Results

**Date:** October 16, 2025  
**Task:** Process 19 articles without narrative_summary through narrative detection system

## Summary

Successfully processed 18 out of 19 articles through the narrative detection pipeline:
- **Total Processed:** 18 articles
- **Matched to Existing Narratives:** 1 article (5.6%)
- **Created New Narratives:** 17 articles (94.4%)
- **Failed:** 1 article (validation error)

## Key Findings

### Matching Performance
- Only **1 article matched** to an existing narrative with similarity ≥ 0.6 threshold
- The matched article had a **0.73 similarity score** (NASDAQ-related content)
- Most articles were historical outliers with unique narratives, as expected

### New Narratives Created
Created 17 new narratives covering diverse topics:
- **Bitcoin/BTC** (3 narratives) - Tax relief, price movements, market analysis
- **Solana/SOL** (2 narratives) - Price performance, market leadership
- **Ethereum/ETH** (2 narratives) - Market movements, price action
- **Regulatory** - SEC guidance on crypto
- **Institutional** - Pantera, Galaxy Digital, NASDAQ tokenization
- **DeFi/Protocols** - Chainlink, SharpLink Gaming
- **Market Analysis** - TradingView, general crypto market updates

### Validation Issues
One article failed validation after 4 retry attempts:
- **Error:** "nucleus_entity 'Crypto' missing salience score"
- **Article:** "PUMP OVERTAKES HYPERLIQUID, GALAXY DIGITAL BUYS $300M SOL..."
- **Issue:** LLM selected "Crypto" as nucleus entity but didn't assign it a salience score

## Technical Implementation

### 1. Fixed 403 Forbidden Errors
Updated `AnthropicProvider._get_completion()` method to include fallback logic:
```python
models_to_try = [
    self.model_name,  # Primary model from config
    "claude-3-5-sonnet-20241022",  # Sonnet 3.5 (Oct 2024)
    "claude-3-5-sonnet-20240620",  # Sonnet 3.5 (June 2024)
    "claude-3-haiku-20240307",  # Haiku 3.0 (fallback)
]
```

This resolved the API access issues where the primary model returned 403 errors.

### 2. Created Processing Script
**File:** `scripts/process_missing_narratives.py`

**Features:**
- Queries articles with null/empty narrative_summary
- Extracts narrative elements using `discover_narrative_from_article()`
- Computes narrative fingerprints for similarity matching
- Matches to existing narratives using 0.6 similarity threshold
- Creates new narratives for articles below threshold
- Includes rate limiting (1 second between articles)

### 3. Narrative Matching Logic
```python
# Fingerprint similarity calculation
if narrative_id and similarity >= 0.6:
    # Match to existing narrative
    await narratives_collection.update_one(
        {"_id": narrative_id},
        {"$addToSet": {"article_ids": article_id}}
    )
else:
    # Create new narrative (similarity < 0.6)
    new_narrative = {
        "nucleus_entity": ...,
        "fingerprint": article_fingerprint,
        "lifecycle_state": "emerging",
        ...
    }
```

## Detailed Results

### Matched Article (1)
| Article | Similarity | Narrative | Action |
|---------|-----------|-----------|--------|
| HYPE HITS ATH, NASDAQ WANTS STOCK TOKENISATION... | 0.73 | NASDAQ | Matched |

### New Narratives Created (17)
| Article Title | Nucleus Entity | Similarity | Status |
|--------------|----------------|------------|--------|
| Dorsey, Lummis Push for Bitcoin Tax Relief | Bitcoin | 0.00 | Created |
| It's not 'too late in the game' to get into crypto | Pantera | 0.17 | Created |
| ETH LEADS MAJORS, CPI TODAY, AVAX DATS COMING | ETH | 0.07 | Created |
| CRYPTO ALL GREEN, PPI TODAY, PUMP & IP LEAD ALTS | Crypto | 0.36 | Created |
| Chainlink Co-Founder Teases Future Collabs | Chainlink | 0.06 | Created |
| SOL GOES HIGHER, HIGHER RATE CUTS MORE LIKELY | NASDAQ | 0.06 | Created |
| SharpLink Gaming Will Be A 'Positive White Swan Event' | SharpLink Gaming | 0.10 | Created |
| BTC HOLDS SUPPORT, MAJORS ALL UP, PUMP +40% | Bitcoin | 0.42 | Created |
| BITCOIN BOUNCES, NFPS TODAY, WLFI BLACKLISTS | Bitcoin | 0.42 | Created |
| POKEMON CARDS ON-CHAIN, CRYPTO STABLE | BTC | 0.21 | Created |
| SOL LEADS, SEC SPEAKS ON CRYPTO GUIDANCE | SEC | 0.51 | Created |
| SOLANA HITS $211 & OUTPREFORMS CRYPTO MAJORS | Solana | 0.36 | Created |
| WLFI LAUNCHES AT $25BN, BTC HOVERS AT $110K | BTC | 0.36 | Created |
| WHY IS CRYPTO DOWN? ETH LEADS CRYPTO LOWER | ETH | 0.42 | Created |
| SOL STRONG, NVIDIA EARNINGS MIXED, CRO UP 50% | Solana | 0.06 | Created |
| ETHEREUM IS SENDING! IS SOLANA NEXT? | Ethereum | 0.36 | Created |
| Twitter User Claims TradingView Has Ignored Fibonacci | TradingView | 0.00 | Created |

### Failed Article (1)
| Article | Error | Attempts |
|---------|-------|----------|
| PUMP OVERTAKES HYPERLIQUID, GALAXY DIGITAL BUYS $300M SOL | nucleus_entity 'Crypto' missing salience score | 4/4 |

## Observations

### 1. Low Matching Rate
- Only 5.6% of articles matched to existing narratives
- This confirms these are **historical outliers** with unique narratives
- Most similarity scores were below 0.5, indicating distinct narrative themes

### 2. Diverse Narrative Landscape
- Articles cover a wide range of topics and entities
- Many are market update/commentary style articles with generic nucleus entities (BTC, ETH, Crypto)
- Some focus on specific entities (Chainlink, TradingView, SharpLink Gaming)

### 3. Validation Challenges
- Generic nucleus entities like "Crypto" can cause validation issues
- LLM sometimes fails to assign salience scores to all actors
- Retry logic helps but doesn't always resolve validation errors

## Recommendations

### 1. Improve Nucleus Entity Selection
Consider adding stricter guidelines for nucleus entity selection:
- Discourage generic terms like "Crypto" or "Market"
- Prefer specific entities (protocols, companies, assets)
- Add validation to reject overly generic nucleus entities

### 2. Handle Generic Market Updates
Articles with titles like "CRYPTO ALL GREEN" or "BTC HOLDS SUPPORT" are market updates rather than narrative-driven news. Consider:
- Creating a special "Market Update" category
- Clustering these separately from narrative-driven articles
- Using different matching criteria for market updates

### 3. Monitor New Narrative Quality
With 17 new narratives created, review their quality:
- Check if any should be merged (e.g., multiple Bitcoin narratives)
- Verify lifecycle states are appropriate
- Ensure fingerprints are well-formed

## Files Modified

1. **`src/crypto_news_aggregator/llm/anthropic.py`**
   - Added fallback logic to `_get_completion()` method
   - Handles 403 Forbidden errors by trying alternative models

2. **`scripts/process_missing_narratives.py`** (New)
   - Script to process articles without narrative_summary
   - Includes narrative matching and creation logic

## Next Steps

1. ✅ **Process missing narratives** - Complete
2. 🔄 **Review new narratives** - Check quality and consider merging similar ones
3. 🔄 **Fix validation issue** - Improve prompt to avoid generic nucleus entities
4. 🔄 **Monitor narrative lifecycle** - Ensure new narratives transition appropriately

## Usage

To run the script again in the future:
```bash
poetry run python scripts/process_missing_narratives.py
```

The script will:
- Query articles with null/empty narrative_summary
- Extract narrative elements
- Match to existing narratives (≥0.6 similarity)
- Create new narratives (<0.6 similarity)
- Report detailed results
