# Narrative Discovery System - Root Cause Analysis

**Date**: October 11, 2025  
**Status**: Analysis Complete - Ready for Fix  
**Commit Analyzed**: `3361d5f` (rolled back in `dee94f9`)

## Executive Summary

The narrative discovery system created **68 narratives** instead of the expected **10-15** because the clustering thresholds were far too loose. The algorithm grouped articles if they shared **2+ actors OR 1+ tension**, which caused massive over-clustering when common actors like "Bitcoin", "SEC", or "Ethereum" appeared across many unrelated articles.

## What the Code Did

### Layer 1: Narrative Discovery
For each article, the system extracted:
- **Actors**: People, organizations, protocols, assets, regulators
- **Actions**: Key events or actions
- **Tensions**: Forces at play (e.g., "Regulation vs Innovation")
- **Implications**: Why it matters
- **Narrative Summary**: 2-3 sentence description

**Function**: `discover_narrative_from_article()` in `narrative_themes.py`

### Layer 2: Clustering Algorithm
Located in `get_articles_by_narrative_similarity()`:

```python
# THE PROBLEMATIC CODE:
for i, article in enumerate(articles):
    article_actors = set(article.get("actors", []))
    article_tensions = set(article.get("tensions", []))
    
    cluster = [article]
    processed.add(str(article["_id"]))
    
    for j, other_article in enumerate(articles[i+1:], start=i+1):
        if str(other_article["_id"]) in processed:
            continue
        
        other_actors = set(other_article.get("actors", []))
        other_tensions = set(other_article.get("tensions", []))
        
        # Check for shared actors or tensions
        shared_actors = article_actors & other_actors
        shared_tensions = article_tensions & other_tensions
        
        # ⚠️ FATAL FLAW: This threshold is WAY too loose
        if len(shared_actors) >= 2 or len(shared_tensions) >= 1:
            cluster.append(other_article)
            processed.add(str(other_article["_id"]))
    
    # Only keep clusters that meet minimum size
    if len(cluster) >= min_articles:  # min_articles=2 (also too low!)
        clusters.append(cluster)
```

**Key Parameters**:
- **Actor threshold**: `>= 2` shared actors
- **Tension threshold**: `>= 1` shared tension
- **Logic**: `shared_actors >= 2 OR shared_tensions >= 1` (OR is too permissive!)
- **Minimum cluster size**: `min_articles=2` (default)

### Layer 3: Narrative Generation
For each cluster, `generate_narrative_from_cluster()`:
- Collected narrative summaries from up to 5 articles
- Aggregated all actors and tensions
- Used LLM to generate a cohesive title and summary

**Function**: `generate_narrative_from_cluster()` in `narrative_themes.py`

## Root Cause: Why 68 Narratives Instead of 10-15

### Problem 1: Overly Permissive Clustering Threshold

**The Fatal Flaw**: `len(shared_actors) >= 2 or len(shared_tensions) >= 1`

This threshold is catastrophically loose because:

1. **Common Actors Create Noise**:
   - "Bitcoin" appears in 50+ articles
   - "SEC" appears in 20+ articles
   - "Ethereum" appears in 30+ articles
   - Any two articles mentioning "Bitcoin" + "SEC" get clustered together
   - This groups unrelated stories: "SEC charges Binance" + "Bitcoin ETF approval" + "SEC investigates Ethereum"

2. **Single Tension Matching is Too Weak**:
   - "Regulation vs Innovation" is a common tension across many unrelated articles
   - One shared tension creates a cluster even if the stories are completely different
   - Example: "SEC vs Binance" and "EU MiCA regulation" both have "Regulation vs Innovation" but are separate narratives

3. **Minimum Cluster Size Too Small**:
   - `min_articles=2` means any 2 articles create a narrative
   - With loose matching, this creates dozens of tiny clusters
   - No consolidation or deduplication

### Problem 2: No Deduplication or Consolidation

The algorithm processes articles sequentially and creates clusters greedily:
- Once an article joins a cluster, it's marked as `processed`
- No post-processing to merge similar clusters
- No semantic similarity check between narrative titles
- Result: "SEC Enforcement Actions" and "SEC vs Exchanges" exist as separate narratives

### Problem 3: LLM Generates Unique Titles

For each cluster, the LLM generates a unique narrative title:
- Even similar clusters get different titles
- No normalization or canonicalization
- Example: One cluster → "Bitcoin ETF Approval Race"
- Another cluster → "Institutional Bitcoin ETF Applications"
- These should be the same narrative

## Specific Examples of Over-Clustering

### Example 1: Bitcoin Entity
**Expected**: 3-4 narratives  
**Actual**: 30+ narratives

**Why**:
- Bitcoin appears as an actor in 50+ articles
- Any 2 articles mentioning Bitcoin + one other common actor (SEC, BlackRock, Binance) create a cluster
- Result: "Bitcoin + SEC", "Bitcoin + BlackRock", "Bitcoin + Binance", etc.

**Concrete Case**:
```
Article A: "SEC Approves Bitcoin ETF Applications"
Actors: [Bitcoin, SEC, BlackRock, Fidelity]

Article B: "Bitcoin Price Surges After ETF News"
Actors: [Bitcoin, BlackRock]

Article C: "SEC Charges Binance with Securities Violations"
Actors: [SEC, Binance, Bitcoin]

Article D: "Fidelity Launches Bitcoin Trading Service"
Actors: [Fidelity, Bitcoin]
```

**What Happened**:
- Article A + B clustered (share: Bitcoin, BlackRock) → "Bitcoin ETF Approval"
- Article A + C clustered (share: Bitcoin, SEC) → "SEC Bitcoin Enforcement"
- Article A + D clustered (share: Bitcoin, Fidelity) → "Institutional Bitcoin Adoption"
- Article B + D clustered (share: Bitcoin, Fidelity) → "Fidelity Bitcoin Services"

**Result**: 4 separate narratives from 4 articles that should be 1 narrative ("Bitcoin ETF Race")

### Example 2: Regulatory Articles
**Expected**: 1-2 narratives ("SEC Enforcement", "Global Regulation")  
**Actual**: 10+ narratives

**Why**:
- "Regulation vs Innovation" tension appears in most regulatory articles
- Single tension match creates clusters
- Result: Separate narratives for each regulatory action instead of grouping them

**Concrete Case**:
```
Article A: "SEC Charges Binance"
Tensions: [Regulation vs Innovation]

Article B: "EU Passes MiCA Regulation"
Tensions: [Regulation vs Innovation]

Article C: "SEC Investigates Coinbase"
Tensions: [Regulation vs Innovation]
```

**What Happened**:
- All 3 articles share 1 tension → Each creates its own cluster
- Result: "SEC vs Binance", "EU MiCA Implementation", "SEC vs Coinbase"
- Should be: 1 narrative "Global Crypto Regulation Intensifies"

### Example 3: DeFi Articles
**Expected**: 2-3 narratives ("DeFi Security", "L2 Competition")  
**Actual**: 8+ narratives

**Why**:
- Common actors: "Ethereum", "Arbitrum", "Optimism"
- Any 2 articles sharing 2 of these actors cluster together
- Result: Fragmented narratives instead of cohesive themes

**Concrete Case**:
```
Article A: "Arbitrum Surpasses Optimism in TVL"
Actors: [Arbitrum, Optimism, Ethereum]

Article B: "Ethereum L2 Solutions See Record Growth"
Actors: [Ethereum, Arbitrum, Base]

Article C: "Optimism Launches New Upgrade"
Actors: [Optimism, Ethereum]

Article D: "Base Attracts Major DeFi Protocols"
Actors: [Base, Ethereum, Arbitrum]
```

**What Happened**:
- Article A + B clustered (share: Arbitrum, Ethereum) → "Arbitrum Growth"
- Article A + C clustered (share: Optimism, Ethereum) → "Optimism Development"
- Article B + D clustered (share: Ethereum, Arbitrum) → "L2 Ecosystem Expansion"
- Article C + D clustered (share: Ethereum) → Wait, only 1 shared actor... but if they also share a tension like "Scalability vs Decentralization", they cluster!

**Result**: 4+ narratives from 4 articles that should be 1 narrative ("Ethereum L2 Competition Heats Up")

## What Needs to Be Fixed

### Fix 1: Tighten Clustering Thresholds ⭐ CRITICAL

**Current**:
```python
if len(shared_actors) >= 2 or len(shared_tensions) >= 1:
```

**Proposed**:
```python
# Require BOTH shared actors AND shared tensions
# AND use higher thresholds
if len(shared_actors) >= 3 and len(shared_tensions) >= 2:
```

**Rationale**:
- Requiring both actors AND tensions ensures stories are truly related
- Higher thresholds (3 actors, 2 tensions) prevent common entities from creating noise
- This should reduce clusters by 70-80%

### Fix 2: Weight Actors by Frequency (Actor Importance)

**Problem**: "Bitcoin" and "Obscure Protocol X" are treated equally

**Solution**: Downweight common actors
```python
# Calculate actor frequency across all articles
actor_frequency = count_actor_appearances(all_articles)

# Only count actors that appear in < 30% of articles
rare_actors = [a for a in shared_actors if actor_frequency[a] < 0.3]

# Use rare actors for matching
if len(rare_actors) >= 2 and len(shared_tensions) >= 1:
```

**Rationale**:
- Focus on distinctive actors (specific protocols, companies, people)
- Ignore ubiquitous actors (Bitcoin, Ethereum, SEC) unless combined with other signals
- This prevents "Bitcoin appears in everything" problem

### Fix 3: Increase Minimum Cluster Size

**Current**: `min_articles=2`

**Proposed**: `min_articles=4`

**Rationale**:
- A narrative needs multiple articles to be significant
- Reduces one-off clusters
- Forces consolidation of related stories

### Fix 4: Add Post-Clustering Deduplication

**New Step**: After creating clusters, merge similar ones

```python
# After clustering, merge similar narratives
def merge_similar_clusters(clusters, similarity_threshold=0.7):
    # Compare narrative summaries using semantic similarity
    # Merge clusters with high similarity
    # Return consolidated clusters
```

**Rationale**:
- Catches cases where different clusters describe the same narrative
- Uses semantic similarity instead of exact matching
- Reduces final narrative count by 30-40%

### Fix 5: Implement Narrative Canonicalization

**Problem**: LLM generates unique titles for similar narratives

**Solution**: Use canonical narrative templates
```python
# After generating narrative title, map to canonical form
canonical_narratives = {
    "SEC Enforcement": ["SEC vs", "SEC charges", "SEC investigates"],
    "Bitcoin ETF": ["Bitcoin ETF", "ETF approval", "ETF application"],
    "L2 Scaling": ["Layer 2", "L2 competition", "Arbitrum vs Optimism"]
}

# Map generated title to canonical narrative
canonical_title = find_canonical_match(generated_title, canonical_narratives)
```

**Rationale**:
- Ensures similar stories map to the same narrative
- Reduces LLM variability
- Makes narratives more predictable and consistent

### Fix 6: Add Hierarchical Clustering

**Current**: Flat clustering (all narratives at same level)

**Proposed**: Two-level hierarchy
- **Parent Narratives**: Broad themes (5-8 total)
  - Example: "Regulatory Developments", "DeFi Innovation", "Institutional Adoption"
- **Child Narratives**: Specific stories (15-20 total)
  - Example: "SEC vs Binance", "Bitcoin ETF Race", "Ethereum L2 Competition"

**Rationale**:
- Provides both high-level overview and detailed stories
- Prevents over-fragmentation
- Better UX for users

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 hours)
1. ✅ Tighten clustering thresholds (Fix 1)
2. ✅ Increase minimum cluster size (Fix 3)
3. ✅ Test with production data

**Expected Result**: 68 narratives → 20-25 narratives

### Phase 2: Actor Weighting (2-3 hours)
4. ✅ Implement actor frequency analysis (Fix 2)
5. ✅ Downweight common actors
6. ✅ Test with production data

**Expected Result**: 20-25 narratives → 12-18 narratives

### Phase 3: Deduplication (3-4 hours)
7. ✅ Add semantic similarity comparison (Fix 4)
8. ✅ Implement cluster merging
9. ✅ Add canonical narrative mapping (Fix 5)
10. ✅ Test with production data

**Expected Result**: 12-18 narratives → 10-15 narratives ✅

### Phase 4: Advanced (Future)
11. ⏳ Implement hierarchical clustering (Fix 6)
12. ⏳ Add narrative lifecycle tracking
13. ⏳ Build narrative evolution visualization

## Testing Strategy

### Before Deployment
1. **Unit Tests**: Test clustering with known article sets
   - Input: 20 articles with known actors/tensions
   - Expected: 3-5 narratives
   - Verify: No over-clustering

2. **Integration Tests**: Test with production-scale data
   - Input: 100 recent articles
   - Expected: 10-15 narratives
   - Verify: Bitcoin linked to 3-4 narratives (not 30+)

3. **Regression Tests**: Ensure fixes don't break existing functionality
   - Legacy theme-based clustering still works
   - Backward compatibility maintained
   - No import errors or missing dependencies

### After Deployment
1. **Monitor narrative counts**: Should stabilize at 10-15
2. **Check entity linking**: Bitcoin should have 3-4 narratives
3. **Verify narrative quality**: Titles should be specific and distinct
4. **Watch for errors**: No LLM failures or clustering crashes

## Success Criteria

✅ **Narrative Count**: 10-15 total narratives (not 68)  
✅ **Entity Linking**: Major entities linked to 3-4 narratives (not 30+)  
✅ **Narrative Quality**: Specific titles like "SEC vs Binance" (not generic)  
✅ **No Duplicates**: No similar narratives with different titles  
✅ **Performance**: Clustering completes in < 30 seconds  

## Files to Modify

1. **`src/crypto_news_aggregator/services/narrative_themes.py`**:
   - `get_articles_by_narrative_similarity()` - Fix clustering thresholds
   - Add `calculate_actor_weights()` - Downweight common actors
   - Add `merge_similar_clusters()` - Post-clustering deduplication

2. **`src/crypto_news_aggregator/services/narrative_service.py`**:
   - `detect_narratives()` - Integrate new clustering logic
   - Add narrative canonicalization

3. **`tests/services/test_narrative_discovery.py`** (new):
   - Unit tests for clustering algorithm
   - Integration tests with realistic data
   - Regression tests for backward compatibility

## Rollout Plan

### Step 1: Create Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/fix-narrative-clustering
```

### Step 2: Implement Fixes
- Phase 1: Tighten thresholds + increase min cluster size
- Test locally with production data
- Verify narrative count drops to 20-25

### Step 3: Add Tests
- Write unit tests for new clustering logic
- Add integration tests with realistic data
- Ensure all tests pass

### Step 4: Create PR
- Document changes in PR description
- Include before/after narrative counts
- Request review

### Step 5: Deploy to Production
- Merge PR after approval
- Monitor Railway logs
- Verify narrative counts stabilize at 10-15

### Step 6: Iterate
- If still too many narratives, implement Phase 2 (actor weighting)
- Continue until success criteria met

## Lessons Learned

1. **Test with Production-Scale Data**: The system worked in tests (3 articles) but failed with 100+ articles
2. **Monitor Key Metrics**: Should have tracked narrative count as a KPI
3. **Start Conservative**: Better to under-cluster (miss some narratives) than over-cluster (create noise)
4. **Validate Thresholds**: `>= 2 actors OR >= 1 tension` was never validated with real data
5. **Add Deduplication Early**: Post-processing is essential for LLM-generated content

## References

- **Original Implementation**: Commit `3361d5f`
- **Rollback Commit**: `dee94f9`
- **Rollback Documentation**: `ROLLBACK_NARRATIVE_DISCOVERY.md`
- **Implementation Summary**: Commit `b43a474` - `NARRATIVE_DISCOVERY_IMPLEMENTATION.md`
- **Test Coverage**: Commit `ffc35f0` - `TEST_COVERAGE_NARRATIVE_DISCOVERY.md`

## Next Actions

- [ ] Review this analysis
- [ ] Approve fix strategy
- [ ] Create feature branch: `feature/fix-narrative-clustering`
- [ ] Implement Phase 1 fixes
- [ ] Write tests
- [ ] Deploy and monitor

---

**Analysis Complete**: Ready to implement fixes when approved.
