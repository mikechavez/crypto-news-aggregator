#!/usr/bin/env python3
"""
Demonstration of the semantic boost feature in fingerprint similarity calculation.

This script shows how the semantic boost helps narratives about the same core entity
merge even when they have minimal actor overlap.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.services.narrative_themes import calculate_fingerprint_similarity


def demo_semantic_boost():
    """Demonstrate the semantic boost feature with real-world examples."""
    
    print("=" * 80)
    print("SEMANTIC BOOST DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Example 1: Same nucleus, minimal actor overlap
    print("Example 1: Two SEC narratives with different actors")
    print("-" * 80)
    
    fp1_sec = {
        'nucleus_entity': 'SEC',
        'top_actors': ['SEC', 'Binance', 'CZ'],
        'key_actions': ['filed lawsuit', 'alleged securities violations']
    }
    
    fp2_sec = {
        'nucleus_entity': 'SEC',
        'top_actors': ['SEC', 'Coinbase', 'Brian Armstrong'],
        'key_actions': ['enforcement action', 'regulatory pressure']
    }
    
    similarity_sec = calculate_fingerprint_similarity(fp1_sec, fp2_sec)
    
    print(f"Fingerprint 1: {fp1_sec['nucleus_entity']} - Actors: {fp1_sec['top_actors']}")
    print(f"Fingerprint 2: {fp2_sec['nucleus_entity']} - Actors: {fp2_sec['top_actors']}")
    print(f"\nSimilarity Score: {similarity_sec:.3f}")
    print(f"  - Nucleus match: 0.45 (both are 'SEC')")
    print(f"  - Actor overlap: ~0.06 (only 'SEC' overlaps, 1/5 Jaccard)")
    print(f"  - Action overlap: 0.00 (no common actions)")
    print(f"  - Semantic boost: +0.10 (same nucleus entity)")
    print(f"  - Total: ~0.61 ✓ (likely to merge)")
    print()
    
    # Example 2: Case-insensitive matching
    print("Example 2: Case-insensitive nucleus matching")
    print("-" * 80)
    
    fp1_btc = {
        'nucleus_entity': 'Bitcoin',
        'top_actors': ['MicroStrategy', 'Saylor'],
        'key_actions': ['corporate buying', 'treasury allocation']
    }
    
    fp2_btc = {
        'nucleus_entity': 'BITCOIN',  # Different case
        'top_actors': ['BlackRock', 'Fidelity'],
        'key_actions': ['ETF approval', 'institutional adoption']
    }
    
    similarity_btc = calculate_fingerprint_similarity(fp1_btc, fp2_btc)
    
    print(f"Fingerprint 1: {fp1_btc['nucleus_entity']} - Actors: {fp1_btc['top_actors']}")
    print(f"Fingerprint 2: {fp2_btc['nucleus_entity']} - Actors: {fp2_btc['top_actors']}")
    print(f"\nSimilarity Score: {similarity_btc:.3f}")
    print(f"  - Nucleus match: 0.00 (case mismatch, 'Bitcoin' != 'BITCOIN')")
    print(f"  - Actor overlap: 0.00 (no common actors)")
    print(f"  - Action overlap: 0.00 (no common actions)")
    print(f"  - Semantic boost: +0.10 (case-insensitive match)")
    print(f"  - Total: 0.10 (may not merge alone, but helps)")
    print()
    
    # Example 3: Different nucleus - no boost
    print("Example 3: Different nucleus entities - no semantic boost")
    print("-" * 80)
    
    fp1_eth = {
        'nucleus_entity': 'Ethereum',
        'top_actors': ['Vitalik', 'Ethereum Foundation'],
        'key_actions': ['protocol upgrade', 'EIP implementation']
    }
    
    fp2_sol = {
        'nucleus_entity': 'Solana',
        'top_actors': ['Solana Labs', 'Anatoly'],
        'key_actions': ['network outage', 'validator restart']
    }
    
    similarity_diff = calculate_fingerprint_similarity(fp1_eth, fp2_sol)
    
    print(f"Fingerprint 1: {fp1_eth['nucleus_entity']} - Actors: {fp1_eth['top_actors']}")
    print(f"Fingerprint 2: {fp2_sol['nucleus_entity']} - Actors: {fp2_sol['top_actors']}")
    print(f"\nSimilarity Score: {similarity_diff:.3f}")
    print(f"  - Nucleus match: 0.00 (different entities)")
    print(f"  - Actor overlap: 0.00 (no common actors)")
    print(f"  - Action overlap: 0.00 (no common actions)")
    print(f"  - Semantic boost: 0.00 (no boost applied)")
    print(f"  - Total: 0.00 ✗ (will not merge)")
    print()
    
    # Example 4: High similarity with boost
    print("Example 4: High similarity - all components match")
    print("-" * 80)
    
    fp1_defi = {
        'nucleus_entity': 'Uniswap',
        'top_actors': ['Uniswap', 'Aave', 'Compound'],
        'key_actions': ['TVL growth', 'liquidity mining', 'yield farming']
    }
    
    fp2_defi = {
        'nucleus_entity': 'Uniswap',
        'top_actors': ['Uniswap', 'Aave', 'MakerDAO'],
        'key_actions': ['TVL growth', 'liquidity mining', 'protocol fees']
    }
    
    similarity_defi = calculate_fingerprint_similarity(fp1_defi, fp2_defi)
    
    print(f"Fingerprint 1: {fp1_defi['nucleus_entity']} - Actors: {fp1_defi['top_actors']}")
    print(f"Fingerprint 2: {fp2_defi['nucleus_entity']} - Actors: {fp2_defi['top_actors']}")
    print(f"\nSimilarity Score: {similarity_defi:.3f}")
    print(f"  - Nucleus match: 0.45 (both are 'Uniswap')")
    print(f"  - Actor overlap: ~0.18 (2/4 Jaccard * 0.35 weight)")
    print(f"  - Action overlap: ~0.08 (2/4 Jaccard * 0.2 weight)")
    print(f"  - Semantic boost: +0.10 (same nucleus entity)")
    print(f"  - Total: ~0.81 ✓✓ (high confidence merge)")
    print()
    
    print("=" * 80)
    print("KEY TAKEAWAYS")
    print("=" * 80)
    print("1. Semantic boost (+0.1) helps narratives about the same entity merge")
    print("2. Case-insensitive matching ensures 'Bitcoin' and 'BITCOIN' get the boost")
    print("3. The boost is significant enough to push borderline cases over merge thresholds")
    print("4. Different entities get no boost, maintaining narrative separation")
    print("=" * 80)


if __name__ == "__main__":
    demo_semantic_boost()
