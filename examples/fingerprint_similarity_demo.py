#!/usr/bin/env python3
"""
Demo script showing how to use calculate_fingerprint_similarity.

This demonstrates the fingerprint similarity calculation for determining
if two narrative clusters should be merged.
"""

from crypto_news_aggregator.services.narrative_themes import (
    compute_narrative_fingerprint,
    calculate_fingerprint_similarity
)


def main():
    """Demonstrate fingerprint similarity calculation."""
    
    print("=" * 70)
    print("Narrative Fingerprint Similarity Demo")
    print("=" * 70)
    print()
    
    # Example 1: Two similar SEC regulatory narratives
    print("Example 1: Similar SEC Regulatory Narratives")
    print("-" * 70)
    
    cluster1 = {
        "nucleus_entity": "SEC",
        "actors": {
            "SEC": 5,
            "Binance": 4,
            "Coinbase": 4,
            "Kraken": 3,
            "Gemini": 2
        },
        "actions": [
            "Filed lawsuit against Binance",
            "Alleged securities violations",
            "Requested compliance documentation"
        ]
    }
    
    cluster2 = {
        "nucleus_entity": "SEC",
        "actors": {
            "SEC": 5,
            "Coinbase": 4,
            "Kraken": 3,
            "Gemini": 3,
            "FTX": 2
        },
        "actions": [
            "Filed lawsuit against Coinbase",
            "Enforcement action initiated",
            "Securities violation charges"
        ]
    }
    
    fp1 = compute_narrative_fingerprint(cluster1)
    fp2 = compute_narrative_fingerprint(cluster2)
    
    print(f"Fingerprint 1:")
    print(f"  Nucleus: {fp1['nucleus_entity']}")
    print(f"  Top Actors: {fp1['top_actors']}")
    print(f"  Key Actions: {fp1['key_actions']}")
    print()
    
    print(f"Fingerprint 2:")
    print(f"  Nucleus: {fp2['nucleus_entity']}")
    print(f"  Top Actors: {fp2['top_actors']}")
    print(f"  Key Actions: {fp2['key_actions']}")
    print()
    
    similarity = calculate_fingerprint_similarity(fp1, fp2)
    print(f"Similarity Score: {similarity:.3f}")
    print(f"Recommendation: {'MERGE' if similarity >= 0.6 else 'KEEP SEPARATE'}")
    print()
    print()
    
    # Example 2: Different narratives (DeFi vs Regulation)
    print("Example 2: Different Narratives (DeFi vs Regulation)")
    print("-" * 70)
    
    cluster3 = {
        "nucleus_entity": "Uniswap",
        "actors": {
            "Uniswap": 5,
            "Aave": 4,
            "Compound": 4,
            "MakerDAO": 3,
            "Curve": 3
        },
        "actions": [
            "TVL increased 20%",
            "New protocol launched",
            "Yield farming incentives"
        ]
    }
    
    fp3 = compute_narrative_fingerprint(cluster3)
    
    print(f"Fingerprint 3 (DeFi):")
    print(f"  Nucleus: {fp3['nucleus_entity']}")
    print(f"  Top Actors: {fp3['top_actors']}")
    print(f"  Key Actions: {fp3['key_actions']}")
    print()
    
    similarity2 = calculate_fingerprint_similarity(fp1, fp3)
    print(f"Similarity to SEC Narrative: {similarity2:.3f}")
    print(f"Recommendation: {'MERGE' if similarity2 >= 0.6 else 'KEEP SEPARATE'}")
    print()
    print()
    
    # Example 3: Same nucleus, different actors
    print("Example 3: Same Nucleus, Different Actors")
    print("-" * 70)
    
    cluster4 = {
        "nucleus_entity": "Bitcoin",
        "actors": {
            "Bitcoin": 5,
            "MicroStrategy": 4,
            "Michael Saylor": 3
        },
        "actions": [
            "Corporate treasury allocation",
            "Institutional buying"
        ]
    }
    
    cluster5 = {
        "nucleus_entity": "Bitcoin",
        "actors": {
            "Bitcoin": 5,
            "El Salvador": 4,
            "Nayib Bukele": 3
        },
        "actions": [
            "Nation-state adoption",
            "Legal tender status"
        ]
    }
    
    fp4 = compute_narrative_fingerprint(cluster4)
    fp5 = compute_narrative_fingerprint(cluster5)
    
    print(f"Fingerprint 4 (Corporate Bitcoin):")
    print(f"  Nucleus: {fp4['nucleus_entity']}")
    print(f"  Top Actors: {fp4['top_actors']}")
    print(f"  Key Actions: {fp4['key_actions']}")
    print()
    
    print(f"Fingerprint 5 (Nation-state Bitcoin):")
    print(f"  Nucleus: {fp5['nucleus_entity']}")
    print(f"  Top Actors: {fp5['top_actors']}")
    print(f"  Key Actions: {fp5['key_actions']}")
    print()
    
    similarity3 = calculate_fingerprint_similarity(fp4, fp5)
    print(f"Similarity Score: {similarity3:.3f}")
    print(f"Recommendation: {'MERGE' if similarity3 >= 0.6 else 'KEEP SEPARATE'}")
    print()
    print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()
    print("Similarity Calculation Weights:")
    print("  - Nucleus Entity Match: 30% (binary: 1.0 or 0.0)")
    print("  - Actor Overlap (Jaccard): 50%")
    print("  - Action Overlap (Jaccard): 20%")
    print()
    print("Merge Threshold: 0.6 (60% similarity)")
    print()
    print("Results:")
    print(f"  1. SEC Regulatory Narratives: {similarity:.3f} → {'MERGE' if similarity >= 0.6 else 'SEPARATE'}")
    print(f"  2. SEC vs DeFi: {similarity2:.3f} → {'MERGE' if similarity2 >= 0.6 else 'SEPARATE'}")
    print(f"  3. Bitcoin Narratives: {similarity3:.3f} → {'MERGE' if similarity3 >= 0.6 else 'SEPARATE'}")
    print()


if __name__ == "__main__":
    main()
