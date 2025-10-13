# Narrative Summary Polish - Cost Analysis

## Overview
Added LLM post-polish step to normalize narrative summary tone and style in `generate_narrative_from_cluster()`.

## Implementation Details

### Location
- **File**: `src/crypto_news_aggregator/services/narrative_themes.py`
- **Function**: `generate_narrative_from_cluster()`
- **Line**: After narrative_data creation (~line 918-942)

### What It Does
1. Takes the initial LLM-generated narrative summary
2. Sends it to Claude Haiku with a polish prompt
3. Rewrites summary to be:
   - 1-2 punchy sentences
   - Neutral, headline-like tone
   - Active voice with strong verbs
   - No meta-phrases like "These articles highlight"
   - Professional and dashboard-appropriate

### Failure Handling
- Graceful degradation: If polish fails, keeps original summary
- Logs warning but doesn't break narrative generation
- Validates polished output (must be >10 chars)

## Cost Analysis

### Model Used
- **Model**: Claude 3 Haiku (claude-3-haiku-20240307)
- **Pricing** (as of Oct 2024):
  - Input: $0.25 per 1M tokens ($0.00025 per 1K tokens)
  - Output: $1.25 per 1M tokens ($0.00125 per 1K tokens)

### Per-Narrative Cost Breakdown

#### Input Tokens (Polish Prompt)
- Base prompt template: ~100 tokens
- Original summary: ~50-100 tokens (average 75)
- **Total input per narrative**: ~175 tokens

**Input cost per narrative**: 175 tokens × $0.00025 / 1000 = **$0.000044**

#### Output Tokens (Polished Summary)
- Polished summary: 1-2 sentences = ~30-60 tokens (average 45)
- **Total output per narrative**: ~45 tokens

**Output cost per narrative**: 45 tokens × $0.00125 / 1000 = **$0.000056**

#### Total Cost Per Narrative
**$0.000044 + $0.000056 = $0.0001 (~0.01 cents per narrative)**

### System-Wide Cost Impact

#### Narrative Generation Frequency
Based on current system behavior:
- Narratives generated from article clusters
- Clustering runs periodically (hourly or on-demand)
- Typical cluster count: 5-15 narratives per clustering run

#### Daily Cost Estimates

**Conservative Estimate** (10 narratives/hour):
- Narratives per day: 10 × 24 = 240 narratives
- Daily cost: 240 × $0.0001 = **$0.024/day**
- Monthly cost: $0.024 × 30 = **$0.72/month**

**High Volume Estimate** (20 narratives/hour):
- Narratives per day: 20 × 24 = 480 narratives
- Daily cost: 480 × $0.0001 = **$0.048/day**
- Monthly cost: $0.048 × 30 = **$1.44/month**

**Peak Load Estimate** (50 narratives/hour during backfills):
- Narratives per day: 50 × 24 = 1,200 narratives
- Daily cost: 1,200 × $0.0001 = **$0.12/day**
- Monthly cost: $0.12 × 30 = **$3.60/month**

### Comparison to Existing LLM Costs

#### Current Narrative Generation Cost
Each narrative already makes 1 LLM call to generate title + summary:
- Input: ~500-800 tokens (article snippets + prompt)
- Output: ~100-150 tokens (JSON with title + summary)
- Cost per narrative: ~$0.0003-$0.0005

#### Polish Step Addition
- Adds: $0.0001 per narrative
- **Percentage increase**: ~20-33% increase in per-narrative LLM cost
- **Absolute increase**: Minimal (~$0.72-$3.60/month)

### Total System Cost Impact

#### Before Polish Feature
- Narrative generation: ~$2-5/month (estimated)
- Entity extraction: ~$10-20/month (estimated)
- **Total LLM costs**: ~$12-25/month

#### After Polish Feature
- Narrative generation: ~$2.72-8.60/month (+$0.72-$3.60)
- Entity extraction: ~$10-20/month (unchanged)
- **Total LLM costs**: ~$12.72-28.60/month

**Net increase**: 2.8-14.4% of total LLM budget

## Benefits vs. Cost Trade-off

### Benefits
1. **Consistent tone**: All narrative summaries have professional, dashboard-appropriate style
2. **Better UX**: Removes meta-phrases and passive voice that clutter UI
3. **Quality control**: Ensures summaries are punchy and actionable
4. **Brand consistency**: Maintains uniform voice across all narratives

### Cost Assessment
- **Negligible absolute cost**: <$4/month even at peak load
- **Minimal percentage increase**: ~3-14% of total LLM budget
- **High ROI**: Significant quality improvement for minimal cost

## Optimization Opportunities

If cost becomes a concern, consider:

1. **Conditional polishing**: Only polish narratives with >3 articles
2. **Batch polishing**: Polish multiple summaries in one LLM call
3. **Caching**: Skip polish if summary already matches style guidelines
4. **Rate limiting**: Limit polish to top N narratives by article count

## Monitoring Recommendations

Track these metrics to validate cost estimates:
1. Polish success rate (should be >95%)
2. Polish calls per hour/day
3. Average input/output tokens per polish
4. Total polish cost vs. total LLM cost

## Conclusion

The narrative polish feature adds **$0.0001 per narrative** in LLM costs, resulting in an estimated **$0.72-$3.60/month** system-wide increase. This represents a 2.8-14.4% increase in total LLM costs but provides significant quality improvements to user-facing narrative summaries.

**Recommendation**: Deploy as-is. Cost is negligible and quality benefits are substantial.
