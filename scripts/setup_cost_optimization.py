#!/usr/bin/env python3
"""
Database Migration Script for Cost Optimization

Creates MongoDB collections and indexes for:
1. LLM response caching (llm_cache)
2. API cost tracking (api_costs)

This enables reducing Anthropic API costs from $92/month to under $10/month.

Usage:
    poetry run python scripts/setup_cost_optimization.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from motor.motor_asyncio import AsyncIOMotorClient
import certifi


# ANSI color codes for pretty output
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(text: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_info(text: str):
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def print_warning(text: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_error(text: str):
    """Print an error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_stat(label: str, value: str):
    """Print a statistic."""
    print(f"{Colors.BOLD}{label}:{Colors.END} {value}")


async def setup_collections_and_indexes(mongodb_uri: str):
    """
    Set up MongoDB collections and indexes for cost optimization.
    
    Args:
        mongodb_uri: MongoDB connection string
    """
    print_header("Cost Optimization Database Setup")
    
    # Connect to MongoDB
    print_info("Connecting to MongoDB...")
    client = AsyncIOMotorClient(
        mongodb_uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000
    )
    
    try:
        # Test connection
        await client.admin.command('ping')
        print_success("Connected to MongoDB successfully")
        
        # Get database
        db = client["crypto_news"]
        
        # ========================================
        # 1. Create llm_cache collection
        # ========================================
        print_header("Setting up LLM Cache Collection")
        
        llm_cache = db["llm_cache"]
        
        # Create unique index on cache_key
        print_info("Creating unique index on cache_key...")
        await llm_cache.create_index(
            "cache_key",
            unique=True,
            name="cache_key_unique"
        )
        print_success("Created unique index: cache_key_unique")
        
        # Create TTL index on expires_at (auto-delete expired entries)
        print_info("Creating TTL index on expires_at...")
        await llm_cache.create_index(
            "expires_at",
            expireAfterSeconds=0,  # Delete immediately when expires_at is reached
            name="expires_at_ttl"
        )
        print_success("Created TTL index: expires_at_ttl (auto-deletes expired entries)")
        
        # Create index on created_at for analytics
        print_info("Creating index on created_at...")
        await llm_cache.create_index(
            [("created_at", -1)],
            name="created_at_desc"
        )
        print_success("Created index: created_at_desc")
        
        # ========================================
        # 2. Create api_costs collection
        # ========================================
        print_header("Setting up API Costs Collection")
        
        api_costs = db["api_costs"]
        
        # Create index on timestamp (descending for recent queries)
        print_info("Creating index on timestamp...")
        await api_costs.create_index(
            [("timestamp", -1)],
            name="timestamp_desc"
        )
        print_success("Created index: timestamp_desc")
        
        # Create index on operation
        print_info("Creating index on operation...")
        await api_costs.create_index(
            "operation",
            name="operation_idx"
        )
        print_success("Created index: operation_idx")
        
        # Create index on model
        print_info("Creating index on model...")
        await api_costs.create_index(
            "model",
            name="model_idx"
        )
        print_success("Created index: model_idx")
        
        # Create compound index on timestamp + operation
        print_info("Creating compound index on timestamp + operation...")
        await api_costs.create_index(
            [("timestamp", -1), ("operation", 1)],
            name="timestamp_operation_compound"
        )
        print_success("Created compound index: timestamp_operation_compound")
        
        # ========================================
        # 3. Verify setup with test entries
        # ========================================
        print_header("Verifying Setup")
        
        # Test llm_cache
        print_info("Testing llm_cache collection...")
        test_cache_entry = {
            "cache_key": "test_key_" + datetime.utcnow().isoformat(),
            "response": {"test": "data"},
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=24),
            "hit_count": 0
        }
        
        result = await llm_cache.insert_one(test_cache_entry)
        print_success(f"Inserted test cache entry: {result.inserted_id}")
        
        # Verify we can read it back
        found = await llm_cache.find_one({"_id": result.inserted_id})
        if found:
            print_success("Successfully read back test cache entry")
            # Clean up test entry
            await llm_cache.delete_one({"_id": result.inserted_id})
            print_success("Cleaned up test cache entry")
        else:
            print_error("Failed to read back test cache entry")
        
        # Test api_costs
        print_info("Testing api_costs collection...")
        test_cost_entry = {
            "timestamp": datetime.utcnow(),
            "operation": "test_operation",
            "model": "claude-3-5-haiku-20241022",
            "input_tokens": 100,
            "output_tokens": 50,
            "cost_usd": 0.001,
            "cached": False
        }
        
        result = await api_costs.insert_one(test_cost_entry)
        print_success(f"Inserted test cost entry: {result.inserted_id}")
        
        # Verify we can read it back
        found = await api_costs.find_one({"_id": result.inserted_id})
        if found:
            print_success("Successfully read back test cost entry")
            # Clean up test entry
            await api_costs.delete_one({"_id": result.inserted_id})
            print_success("Cleaned up test cost entry")
        else:
            print_error("Failed to read back test cost entry")
        
        # ========================================
        # 4. Display database statistics
        # ========================================
        print_header("Database Statistics")
        
        # Count articles
        articles_count = await db["articles"].count_documents({})
        print_stat("Total Articles", f"{articles_count:,}")
        
        # Count entities
        entities_count = await db["entity_mentions"].count_documents({})
        print_stat("Total Entity Mentions", f"{entities_count:,}")
        
        # Count narratives
        narratives_count = await db["narratives"].count_documents({})
        print_stat("Total Narratives", f"{narratives_count:,}")
        
        # ========================================
        # 5. Display cost estimates
        # ========================================
        print_header("Cost Optimization Estimates")
        
        print_info("Current Costs (Without Optimization):")
        print_stat("  Monthly API Calls", "~92,000")
        print_stat("  Estimated Cost", "$92/month")
        
        print_info("\nProjected Costs (With Caching):")
        print_stat("  Cache Hit Rate", "~90%")
        print_stat("  Monthly API Calls", "~9,200")
        print_stat("  Estimated Cost", "<$10/month")
        
        print_info("\nSavings:")
        print_stat("  API Calls Saved", "~82,800/month")
        print_stat("  Cost Savings", "~$82/month (89% reduction)")
        
        # ========================================
        # Success summary
        # ========================================
        print_header("Setup Complete!")
        
        print_success("Collections created:")
        print(f"  • {Colors.BOLD}llm_cache{Colors.END} - LLM response caching")
        print(f"  • {Colors.BOLD}api_costs{Colors.END} - API cost tracking")
        
        print_success("\nIndexes created:")
        print(f"  • {Colors.BOLD}llm_cache{Colors.END}:")
        print("    - cache_key (unique)")
        print("    - expires_at (TTL, auto-delete)")
        print("    - created_at (descending)")
        print(f"  • {Colors.BOLD}api_costs{Colors.END}:")
        print("    - timestamp (descending)")
        print("    - operation")
        print("    - model")
        print("    - timestamp + operation (compound)")
        
        print_success("\nNext Steps:")
        print("  1. Implement LLM caching layer in entity extraction")
        print("  2. Implement cost tracking in API calls")
        print("  3. Add cache warming for common queries")
        print("  4. Monitor cache hit rates and costs")
        
    except Exception as e:
        print_error(f"Setup failed: {e}")
        raise
    finally:
        client.close()
        print_info("\nClosed MongoDB connection")


async def main():
    """Main entry point."""
    # Get MongoDB URI from environment
    mongodb_uri = os.getenv("MONGODB_URI")
    
    if not mongodb_uri:
        print_error("MONGODB_URI environment variable not set")
        print_info("Usage: export MONGODB_URI='your_connection_string'")
        print_info("       python scripts/setup_cost_optimization.py")
        sys.exit(1)
    
    # Mask URI for display
    masked_uri = mongodb_uri.split("@")[-1] if "@" in mongodb_uri else mongodb_uri
    print_info(f"Using MongoDB: {masked_uri}")
    
    try:
        await setup_collections_and_indexes(mongodb_uri)
    except Exception as e:
        print_error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
