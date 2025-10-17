#!/usr/bin/env python3
"""
Create missing indexes on narratives collection to fix slow queries.
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crypto_news_aggregator.db.operations.narratives import ensure_indexes

async def main():
    print("Creating indexes on narratives collection...")
    try:
        await ensure_indexes()
        print("✓ Indexes created successfully!")
        print("\nIndexes created:")
        print("  - idx_last_updated (last_updated)")
        print("  - idx_theme_unique (theme, unique)")
        print("  - idx_lifecycle (lifecycle)")
        print("  - idx_lifecycle_state (lifecycle_state)")
        print("  - idx_lifecycle_state_last_updated (lifecycle_state + last_updated)")
        print("  - idx_reawakened_from (reawakened_from)")
    except Exception as e:
        print(f"✗ Error creating indexes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
