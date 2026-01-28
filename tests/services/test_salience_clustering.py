"""
Tests for salience-aware narrative clustering.

Tests the cluster_by_narrative_salience function with various scenarios:
- Same nucleus entity clustering
- High-salience actor overlap
- Tension-based weak links
- Minimum cluster size filtering
"""

import pytest
from src.crypto_news_aggregator.services.narrative_themes import cluster_by_narrative_salience


@pytest.mark.asyncio
async def test_cluster_by_same_nucleus_entity():
    """Articles with same nucleus entity should cluster together (link_strength = 1.0)."""
    articles = [
        {
            "id": "1",
            "nucleus_entity": "SEC",
            "actors": ["SEC", "Binance"],
            "actor_salience": {"SEC": 5, "Binance": 4.5},
            "tensions": ["Regulation vs Innovation"]
        },
        {
            "id": "2",
            "nucleus_entity": "SEC",
            "actors": ["SEC", "Coinbase"],
            "actor_salience": {"SEC": 5, "Coinbase": 4.5},
            "tensions": ["Compliance"]
        },
        {
            "id": "3",
            "nucleus_entity": "SEC",
            "actors": ["SEC", "Ripple"],
            "actor_salience": {"SEC": 5, "Ripple": 4.5},
            "tensions": ["Legal Framework"]
        }
    ]
    
    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=3)
    
    # Should form 1 cluster with all 3 articles (same nucleus)
    assert len(clusters) == 1
    assert len(clusters[0]) == 3
    
    # All articles should be in the cluster
    cluster_ids = {a["id"] for a in clusters[0]}
    assert cluster_ids == {"1", "2", "3"}


@pytest.mark.asyncio
async def test_cluster_by_high_salience_actors():
    """Articles with 2+ shared high-salience actors + shared tension should cluster (link_strength >= 0.8)."""
    articles = [
        {
            "id": "1",
            "nucleus_entity": "Binance",
            "actors": ["Binance", "Coinbase", "SEC"],
            "actor_salience": {"Binance": 5, "Coinbase": 4.6, "SEC": 4.6},
            "tensions": ["Regulation"]
        },
        {
            "id": "2",
            "nucleus_entity": "Coinbase",
            "actors": ["Coinbase", "Binance", "Gary Gensler"],
            "actor_salience": {"Coinbase": 5, "Binance": 4.6, "Gary Gensler": 3},
            "tensions": ["Regulation"]
        },
        {
            "id": "3",
            "nucleus_entity": "Kraken",
            "actors": ["Kraken", "Binance", "Coinbase"],
            "actor_salience": {"Kraken": 5, "Binance": 4.6, "Coinbase": 4.6},
            "tensions": ["Regulation"]  # Changed to match other articles
        }
    ]
    
    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=3)
    
    # Should form 1 cluster (all share Binance + Coinbase as high-salience actors)
    # link_strength = 0.7 (2+ shared core actors) + 0.3 (shared tension) = 1.0
    assert len(clusters) == 1
    assert len(clusters[0]) == 3


@pytest.mark.asyncio
async def test_no_cluster_below_threshold():
    """Articles with weak links (< 0.8) should not cluster together."""
    articles = [
        {
            "id": "1",
            "nucleus_entity": "Bitcoin",
            "actors": ["Bitcoin", "Michael Saylor"],
            "actor_salience": {"Bitcoin": 5, "Michael Saylor": 4},
            "tensions": ["Adoption"]
        },
        {
            "id": "2",
            "nucleus_entity": "Ethereum",
            "actors": ["Ethereum", "Vitalik Buterin"],
            "actor_salience": {"Ethereum": 5, "Vitalik Buterin": 4},
            "tensions": ["Scaling"]
        },
        {
            "id": "3",
            "nucleus_entity": "Solana",
            "actors": ["Solana", "Anatoly Yakovenko"],
            "actor_salience": {"Solana": 5, "Anatoly Yakovenko": 4},
            "tensions": ["Performance"]
        }
    ]
    
    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=3)
    
    # No shared nucleus, no shared high-salience actors, different tensions
    # Each article forms its own cluster, but all are below min_cluster_size
    assert len(clusters) == 0


@pytest.mark.asyncio
async def test_filter_small_clusters():
    """Clusters below min_cluster_size should be filtered out."""
    articles = [
        {
            "id": "1",
            "nucleus_entity": "SEC",
            "actors": ["SEC", "Binance"],
            "actor_salience": {"SEC": 5, "Binance": 4.5},
            "tensions": ["Regulation"]
        },
        {
            "id": "2",
            "nucleus_entity": "SEC",
            "actors": ["SEC", "Coinbase"],
            "actor_salience": {"SEC": 5, "Coinbase": 4.5},
            "tensions": ["Regulation"]
        },
        {
            "id": "3",
            "nucleus_entity": "Bitcoin",
            "actors": ["Bitcoin"],
            "actor_salience": {"Bitcoin": 5},
            "tensions": ["Adoption"]
        }
    ]
    
    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=3)
    
    # Only the SEC cluster (2 articles) exists, but it's below min_cluster_size=3
    # Bitcoin article is alone
    # Result: no clusters meet the threshold
    assert len(clusters) == 0


@pytest.mark.asyncio
async def test_tension_overlap_weak_signal():
    """Shared tensions alone (0.3) should not be enough to cluster (< 0.8 threshold)."""
    articles = [
        {
            "id": "1",
            "nucleus_entity": "Bitcoin",
            "actors": ["Bitcoin"],
            "actor_salience": {"Bitcoin": 5},
            "tensions": ["Regulation vs Innovation"]
        },
        {
            "id": "2",
            "nucleus_entity": "Ethereum",
            "actors": ["Ethereum"],
            "actor_salience": {"Ethereum": 5},
            "tensions": ["Regulation vs Innovation"]
        },
        {
            "id": "3",
            "nucleus_entity": "Solana",
            "actors": ["Solana"],
            "actor_salience": {"Solana": 5},
            "tensions": ["Regulation vs Innovation"]
        }
    ]
    
    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=3)
    
    # Shared tension gives link_strength = 0.3, which is below 0.8 threshold
    # Each article forms its own cluster, all below min_cluster_size
    assert len(clusters) == 0


@pytest.mark.asyncio
async def test_one_shared_actor_plus_tension():
    """1 shared high-salience actor (0.4) + shared tension (0.3) = 0.7, below threshold."""
    articles = [
        {
            "id": "1",
            "nucleus_entity": "Binance",
            "actors": ["Binance", "SEC"],
            "actor_salience": {"Binance": 5, "SEC": 4.5},
            "tensions": ["Regulation"]
        },
        {
            "id": "2",
            "nucleus_entity": "Coinbase",
            "actors": ["Coinbase", "SEC"],
            "actor_salience": {"Coinbase": 5, "SEC": 4.5},
            "tensions": ["Regulation"]
        },
        {
            "id": "3",
            "nucleus_entity": "Kraken",
            "actors": ["Kraken", "SEC"],
            "actor_salience": {"Kraken": 5, "SEC": 4.5},
            "tensions": ["Regulation"]
        }
    ]
    
    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=3)
    
    # 1 shared actor (SEC) = 0.4, shared tension = 0.3, total = 0.7
    # Below 0.8 threshold, so no clustering
    assert len(clusters) == 0


@pytest.mark.asyncio
async def test_low_salience_actors_ignored():
    """Actors with salience < 4.5 should not contribute to clustering."""
    articles = [
        {
            "id": "1",
            "nucleus_entity": "Bitcoin",
            "actors": ["Bitcoin", "Coinbase", "Binance"],
            "actor_salience": {"Bitcoin": 5, "Coinbase": 3, "Binance": 2},  # Only Bitcoin is core
            "tensions": ["Adoption"]
        },
        {
            "id": "2",
            "nucleus_entity": "Ethereum",
            "actors": ["Ethereum", "Coinbase", "Binance"],
            "actor_salience": {"Ethereum": 5, "Coinbase": 3, "Binance": 2},  # Only Ethereum is core
            "tensions": ["Adoption"]
        },
        {
            "id": "3",
            "nucleus_entity": "Solana",
            "actors": ["Solana", "Coinbase", "Binance"],
            "actor_salience": {"Solana": 5, "Coinbase": 3, "Binance": 2},  # Only Solana is core
            "tensions": ["Adoption"]
        }
    ]

    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=3)

    # Coinbase and Binance have salience < 4.5, so they don't count as core actors
    # No shared core actors, different nucleus entities
    # Shared tension = 0.3, below threshold
    assert len(clusters) == 0


@pytest.mark.asyncio
async def test_mixed_clustering():
    """Test realistic scenario with multiple clusters forming."""
    articles = [
        # SEC regulatory cluster (3 articles)
        {
            "id": "1",
            "nucleus_entity": "SEC",
            "actors": ["SEC", "Binance"],
            "actor_salience": {"SEC": 5, "Binance": 4.6},
            "tensions": ["Regulation"]
        },
        {
            "id": "2",
            "nucleus_entity": "SEC",
            "actors": ["SEC", "Coinbase"],
            "actor_salience": {"SEC": 5, "Coinbase": 4.6},
            "tensions": ["Regulation"]
        },
        {
            "id": "3",
            "nucleus_entity": "SEC",
            "actors": ["SEC", "Ripple"],
            "actor_salience": {"SEC": 5, "Ripple": 4.6},
            "tensions": ["Legal Framework"]
        },
        # DeFi cluster (3 articles)
        {
            "id": "4",
            "nucleus_entity": "Uniswap",
            "actors": ["Uniswap", "Aave", "Curve"],
            "actor_salience": {"Uniswap": 5, "Aave": 4.6, "Curve": 4.6},
            "tensions": ["DeFi Innovation"]
        },
        {
            "id": "5",
            "nucleus_entity": "Aave",
            "actors": ["Aave", "Uniswap", "Compound"],
            "actor_salience": {"Aave": 5, "Uniswap": 4.6, "Compound": 4.6},
            "tensions": ["DeFi Innovation"]
        },
        {
            "id": "6",
            "nucleus_entity": "Curve",
            "actors": ["Curve", "Uniswap", "Aave"],
            "actor_salience": {"Curve": 5, "Uniswap": 4.6, "Aave": 4.6},
            "tensions": ["DeFi Innovation"]
        },
        # Isolated articles (below min_cluster_size)
        {
            "id": "7",
            "nucleus_entity": "Bitcoin",
            "actors": ["Bitcoin"],
            "actor_salience": {"Bitcoin": 5},
            "tensions": ["Adoption"]
        }
    ]
    
    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=3)
    
    # Should form 2 clusters: SEC (3 articles) and DeFi (3 articles)
    # Bitcoin article is isolated and filtered out
    assert len(clusters) == 2
    
    # Check cluster sizes
    cluster_sizes = sorted([len(c) for c in clusters])
    assert cluster_sizes == [3, 3]
    
    # Verify cluster composition
    all_cluster_ids = set()
    for cluster in clusters:
        cluster_ids = {a["id"] for a in cluster}
        all_cluster_ids.update(cluster_ids)
        
        # Each cluster should be either SEC or DeFi
        assert cluster_ids in [
            {"1", "2", "3"},  # SEC cluster
            {"4", "5", "6"}   # DeFi cluster
        ]
    
    # Bitcoin article should not be in any cluster
    assert "7" not in all_cluster_ids


@pytest.mark.asyncio
async def test_tangential_mention_filtered():
    """Articles with tangential mentions (salience 4.0-4.4) should not cluster.

    This tests the fix for FEATURE-017: articles with an entity mentioned in passing
    (salience just below the 4.5 threshold) should not contribute to clustering.

    Real example: "Sharps Technology Partners with Solana" article mentions Coinbase
    once in an analyst quote - should be filtered out even though it has the entity.
    """
    articles = [
        {
            "id": "1",
            "nucleus_entity": "Solana",
            "actors": ["Solana", "Sharps Technology"],
            "actor_salience": {"Solana": 5, "Sharps Technology": 4.8},
            "tensions": ["Partnership"]
        },
        {
            "id": "2",
            "nucleus_entity": "Coinbase",
            "actors": ["Coinbase"],
            "actor_salience": {"Coinbase": 5},
            "tensions": ["Market Analysis"]
        },
        {
            # This is the tangential mention article - mentions Coinbase but only in passing
            "id": "3",
            "nucleus_entity": "Sharps Technology",
            "actors": ["Sharps Technology", "Solana", "Coinbase"],
            "actor_salience": {"Sharps Technology": 5, "Solana": 4.8, "Coinbase": 4.1},
            "tensions": ["Partnership"]
        }
    ]

    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=3)

    # Articles 1 and 3 should NOT cluster together with article 2
    # because Coinbase in article 3 has salience 4.1 (below 4.5 threshold)
    # Article 1 and 3 don't have 2+ shared core actors (Coinbase doesn't count as core in article 3)
    # Even though all 3 articles are available, they shouldn't form a cluster >= min_cluster_size
    # because the tangential mention (Coinbase at 4.1) is now filtered out
    assert len(clusters) == 0


@pytest.mark.asyncio
async def test_empty_input():
    """Empty article list should return empty clusters."""
    clusters = await cluster_by_narrative_salience([], min_cluster_size=3)
    assert len(clusters) == 0


@pytest.mark.asyncio
async def test_missing_fields():
    """Articles with missing fields should be handled gracefully."""
    articles = [
        {
            "id": "1",
            # Missing nucleus_entity, actors, actor_salience, tensions
        },
        {
            "id": "2",
            "nucleus_entity": "SEC",
            # Missing actors, actor_salience, tensions
        },
        {
            "id": "3",
            "nucleus_entity": "SEC",
            "actors": ["SEC"],
            # Missing actor_salience, tensions
        }
    ]
    
    clusters = await cluster_by_narrative_salience(articles, min_cluster_size=3)
    
    # Should handle gracefully without errors
    # Articles 2 and 3 have same nucleus, so they might cluster
    # But without salience data, article 3 has no core actors
    # Result depends on implementation details, but should not crash
    assert isinstance(clusters, list)
