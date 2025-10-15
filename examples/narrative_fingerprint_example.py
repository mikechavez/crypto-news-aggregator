"""
Example usage of compute_narrative_fingerprint function.

This demonstrates how to create a composite fingerprint for narrative clusters
to enable intelligent matching and deduplication.
"""

from datetime import datetime, timezone
from crypto_news_aggregator.services.narrative_themes import compute_narrative_fingerprint


def main():
    """Demonstrate narrative fingerprint computation."""
    
    # Example 1: Cluster with actor salience scores (dict format)
    print("=" * 60)
    print("Example 1: SEC Regulatory Narrative")
    print("=" * 60)
    
    sec_cluster = {
        "nucleus_entity": "SEC",
        "actors": {
            "SEC": 5,
            "Binance": 4,
            "Coinbase": 4,
            "Kraken": 3,
            "Gemini": 3,
            "FTX": 2,
            "Tether": 2,
            "Ripple": 2
        },
        "actions": [
            "Filed lawsuit against major exchanges",
            "Announced new regulatory framework",
            "Issued enforcement actions",
            "Requested additional disclosures",
            "Charged unregistered securities operations"
        ]
    }
    
    fingerprint = compute_narrative_fingerprint(sec_cluster)
    
    print(f"\nNucleus Entity: {fingerprint['nucleus_entity']}")
    print(f"Top 5 Actors (by salience): {fingerprint['top_actors']}")
    print(f"Key Actions (top 3): {fingerprint['key_actions']}")
    print(f"Timestamp: {fingerprint['timestamp']}")
    
    # Example 2: Cluster with actors as list
    print("\n" + "=" * 60)
    print("Example 2: Ethereum Upgrade Narrative")
    print("=" * 60)
    
    eth_cluster = {
        "nucleus_entity": "Ethereum",
        "actors": ["Ethereum", "Vitalik Buterin", "EIP-4844", "Layer 2 protocols"],
        "actions": [
            "Deployed Dencun upgrade",
            "Reduced transaction fees by 90%",
            "Improved scalability for rollups"
        ]
    }
    
    fingerprint = compute_narrative_fingerprint(eth_cluster)
    
    print(f"\nNucleus Entity: {fingerprint['nucleus_entity']}")
    print(f"Top Actors: {fingerprint['top_actors']}")
    print(f"Key Actions: {fingerprint['key_actions']}")
    print(f"Timestamp: {fingerprint['timestamp']}")
    
    # Example 3: Minimal cluster
    print("\n" + "=" * 60)
    print("Example 3: Minimal Narrative")
    print("=" * 60)
    
    minimal_cluster = {
        "nucleus_entity": "Bitcoin",
        "actors": {"Bitcoin": 5, "Michael Saylor": 4},
        "actions": ["Reached new all-time high"]
    }
    
    fingerprint = compute_narrative_fingerprint(minimal_cluster)
    
    print(f"\nNucleus Entity: {fingerprint['nucleus_entity']}")
    print(f"Top Actors: {fingerprint['top_actors']}")
    print(f"Key Actions: {fingerprint['key_actions']}")
    print(f"Timestamp: {fingerprint['timestamp']}")
    
    # Example 4: Demonstrate fingerprint comparison
    print("\n" + "=" * 60)
    print("Example 4: Fingerprint Comparison")
    print("=" * 60)
    
    cluster_a = {
        "nucleus_entity": "DeFi",
        "actors": {"Uniswap": 5, "Aave": 4, "Compound": 3},
        "actions": ["TVL growth", "New protocol launches"]
    }
    
    cluster_b = {
        "nucleus_entity": "DeFi",
        "actors": {"Uniswap": 5, "Curve": 4, "MakerDAO": 3},
        "actions": ["TVL growth", "Governance proposals"]
    }
    
    fp_a = compute_narrative_fingerprint(cluster_a)
    fp_b = compute_narrative_fingerprint(cluster_b)
    
    print("\nCluster A Fingerprint:")
    print(f"  Nucleus: {fp_a['nucleus_entity']}")
    print(f"  Actors: {fp_a['top_actors']}")
    print(f"  Actions: {fp_a['key_actions']}")
    
    print("\nCluster B Fingerprint:")
    print(f"  Nucleus: {fp_b['nucleus_entity']}")
    print(f"  Actors: {fp_b['top_actors']}")
    print(f"  Actions: {fp_b['key_actions']}")
    
    # Calculate similarity
    same_nucleus = fp_a['nucleus_entity'] == fp_b['nucleus_entity']
    shared_actors = set(fp_a['top_actors']) & set(fp_b['top_actors'])
    shared_actions = set(fp_a['key_actions']) & set(fp_b['key_actions'])
    
    print("\nSimilarity Analysis:")
    print(f"  Same nucleus entity: {same_nucleus}")
    print(f"  Shared actors: {shared_actors}")
    print(f"  Shared actions: {shared_actions}")
    print(f"  Could be merged: {same_nucleus and len(shared_actors) >= 1}")


if __name__ == "__main__":
    main()
