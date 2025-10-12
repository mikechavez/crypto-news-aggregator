#!/usr/bin/env python3
"""
Integration test for salience-aware narrative clustering.

This script demonstrates how to use cluster_by_narrative_salience
with real article data from the database.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_news_aggregator.services.narrative_themes import (
    discover_narrative_from_article,
    cluster_by_narrative_salience
)
from crypto_news_aggregator.db.mongodb import mongo_manager
from datetime import datetime, timezone, timedelta


async def test_clustering_with_real_data():
    """Test clustering with real articles from the database."""
    print("🔍 Fetching recent articles with narrative data...")
    
    db = await mongo_manager.get_async_database()
    articles_collection = db.articles
    
    # Get recent articles that have narrative data
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)
    
    cursor = articles_collection.find({
        "published_at": {"$gte": cutoff_time},
        "narrative_data": {"$exists": True}
    }).limit(20)
    
    articles_with_narratives = []
    async for article in cursor:
        narrative_data = article.get("narrative_data", {})
        if narrative_data:
            # Prepare article dict for clustering
            article_dict = {
                "id": str(article["_id"]),
                "title": article.get("title", ""),
                "nucleus_entity": narrative_data.get("nucleus_entity"),
                "actors": narrative_data.get("actors", []),
                "actor_salience": narrative_data.get("actor_salience", {}),
                "tensions": narrative_data.get("tensions", []),
                "published_at": article.get("published_at")
            }
            articles_with_narratives.append(article_dict)
    
    print(f"✅ Found {len(articles_with_narratives)} articles with narrative data")
    
    if len(articles_with_narratives) < 3:
        print("⚠️  Not enough articles for clustering (need at least 3)")
        return
    
    # Test clustering with different min_cluster_size values
    for min_size in [2, 3, 4]:
        print(f"\n{'='*60}")
        print(f"Testing with min_cluster_size={min_size}")
        print(f"{'='*60}")
        
        clusters = await cluster_by_narrative_salience(
            articles_with_narratives,
            min_cluster_size=min_size
        )
        
        print(f"\n📊 Found {len(clusters)} clusters")
        
        for i, cluster in enumerate(clusters, 1):
            print(f"\n🔗 Cluster {i} ({len(cluster)} articles):")
            
            # Get cluster properties
            nucleus_entities = set()
            all_core_actors = set()
            all_tensions = set()
            
            for article in cluster:
                nucleus = article.get("nucleus_entity")
                if nucleus:
                    nucleus_entities.add(nucleus)
                
                # Get core actors (salience >= 4)
                actor_salience = article.get("actor_salience", {})
                core_actors = [
                    actor for actor in article.get("actors", [])
                    if actor_salience.get(actor, 0) >= 4
                ]
                all_core_actors.update(core_actors)
                all_tensions.update(article.get("tensions", []))
            
            print(f"   Nucleus entities: {', '.join(nucleus_entities)}")
            print(f"   Core actors: {', '.join(sorted(all_core_actors))}")
            print(f"   Tensions: {', '.join(sorted(all_tensions))}")
            print(f"\n   Articles:")
            
            for article in cluster[:5]:  # Show first 5 articles
                title = article.get("title", "")[:80]
                nucleus = article.get("nucleus_entity", "N/A")
                print(f"   - [{nucleus}] {title}")
            
            if len(cluster) > 5:
                print(f"   ... and {len(cluster) - 5} more articles")


async def test_clustering_with_sample_data():
    """Test clustering with sample data (no database required)."""
    print("\n" + "="*60)
    print("Testing with sample data (no database)")
    print("="*60)
    
    sample_articles = [
        # SEC enforcement cluster
        {
            "id": "1",
            "title": "SEC Files Lawsuit Against Binance for Securities Violations",
            "nucleus_entity": "SEC",
            "actors": ["SEC", "Binance", "Gary Gensler"],
            "actor_salience": {"SEC": 5, "Binance": 4, "Gary Gensler": 3},
            "tensions": ["Regulation vs Innovation", "Compliance"]
        },
        {
            "id": "2",
            "title": "SEC Targets Coinbase in Regulatory Crackdown",
            "nucleus_entity": "SEC",
            "actors": ["SEC", "Coinbase", "Brian Armstrong"],
            "actor_salience": {"SEC": 5, "Coinbase": 4, "Brian Armstrong": 3},
            "tensions": ["Regulation vs Innovation", "Legal Framework"]
        },
        {
            "id": "3",
            "title": "SEC vs Ripple: Court Ruling Expected Soon",
            "nucleus_entity": "SEC",
            "actors": ["SEC", "Ripple", "Brad Garlinghouse"],
            "actor_salience": {"SEC": 5, "Ripple": 4, "Brad Garlinghouse": 3},
            "tensions": ["Legal Framework", "Securities Classification"]
        },
        # DeFi innovation cluster
        {
            "id": "4",
            "title": "Uniswap Launches V4 with Advanced Features",
            "nucleus_entity": "Uniswap",
            "actors": ["Uniswap", "Aave", "Curve"],
            "actor_salience": {"Uniswap": 5, "Aave": 4, "Curve": 4},
            "tensions": ["DeFi Innovation", "Protocol Competition"]
        },
        {
            "id": "5",
            "title": "Aave Expands to New Blockchain Networks",
            "nucleus_entity": "Aave",
            "actors": ["Aave", "Uniswap", "Compound"],
            "actor_salience": {"Aave": 5, "Uniswap": 4, "Compound": 4},
            "tensions": ["DeFi Innovation", "Cross-chain Integration"]
        },
        {
            "id": "6",
            "title": "Curve Finance Integrates with Major DeFi Protocols",
            "nucleus_entity": "Curve",
            "actors": ["Curve", "Uniswap", "Aave"],
            "actor_salience": {"Curve": 5, "Uniswap": 4, "Aave": 4},
            "tensions": ["DeFi Innovation", "Liquidity Optimization"]
        },
        # Isolated articles (won't cluster)
        {
            "id": "7",
            "title": "Bitcoin Adoption Grows in El Salvador",
            "nucleus_entity": "Bitcoin",
            "actors": ["Bitcoin", "Nayib Bukele"],
            "actor_salience": {"Bitcoin": 5, "Nayib Bukele": 4},
            "tensions": ["Adoption", "Sovereignty"]
        },
        {
            "id": "8",
            "title": "Ethereum Staking Reaches New Milestone",
            "nucleus_entity": "Ethereum",
            "actors": ["Ethereum", "Vitalik Buterin"],
            "actor_salience": {"Ethereum": 5, "Vitalik Buterin": 3},
            "tensions": ["Network Security", "Decentralization"]
        }
    ]
    
    clusters = await cluster_by_narrative_salience(sample_articles, min_cluster_size=3)
    
    print(f"\n📊 Found {len(clusters)} clusters from {len(sample_articles)} articles")
    
    for i, cluster in enumerate(clusters, 1):
        print(f"\n🔗 Cluster {i}: {len(cluster)} articles")
        
        # Get shared properties
        nucleus_entities = {a.get("nucleus_entity") for a in cluster}
        print(f"   Nucleus entities: {', '.join(nucleus_entities)}")
        
        print(f"   Articles:")
        for article in cluster:
            title = article.get("title", "")
            nucleus = article.get("nucleus_entity", "N/A")
            print(f"   - [{nucleus}] {title}")
    
    # Show isolated articles
    clustered_ids = {a["id"] for cluster in clusters for a in cluster}
    isolated = [a for a in sample_articles if a["id"] not in clustered_ids]
    
    if isolated:
        print(f"\n⚠️  {len(isolated)} isolated articles (not in any cluster):")
        for article in isolated:
            title = article.get("title", "")
            nucleus = article.get("nucleus_entity", "N/A")
            print(f"   - [{nucleus}] {title}")


async def main():
    """Run all clustering tests."""
    print("🚀 Salience-Aware Narrative Clustering Integration Test\n")
    
    # Test with sample data (always works)
    await test_clustering_with_sample_data()
    
    # Test with real data (if database is available)
    try:
        await test_clustering_with_real_data()
    except Exception as e:
        print(f"\n⚠️  Could not test with real data: {e}")
        print("   (This is expected if database is not configured)")
    
    print("\n✅ Integration test complete!")


if __name__ == "__main__":
    asyncio.run(main())
