#!/usr/bin/env python3
"""
Add MongoDB unique index on narrative_fingerprint.nucleus_entity to prevent duplicates.

This script creates a unique index on the narratives collection to ensure that
no two narratives can have the same nucleus_entity in their fingerprint. This
provides database-level protection against duplicate narratives.

The index is created with sparse=True to allow narratives without a fingerprint
(though the application-level validation should prevent this).

Usage:
    poetry run python scripts/add_fingerprint_validation_index.py
"""

import asyncio
import sys
import os
from pymongo import ASCENDING
from pymongo.errors import OperationFailure

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))

from crypto_news_aggregator.db.mongodb import mongo_manager


async def create_fingerprint_index():
    """
    Create a unique index on narrative_fingerprint.nucleus_entity.
    
    The index ensures that:
    1. No two narratives can have the same nucleus_entity
    2. Narratives without a fingerprint are allowed (sparse=True)
    3. Database-level duplicate prevention
    """
    print("=" * 70)
    print("Creating unique index on narrative_fingerprint.nucleus_entity")
    print("=" * 70)
    print()
    
    try:
        # Initialize MongoDB connection
        await mongo_manager.initialize()
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Check existing indexes
        print("Checking existing indexes...")
        existing_indexes = await narratives_collection.index_information()
        
        index_name = "idx_fingerprint_nucleus_entity_unique"
        
        if index_name in existing_indexes:
            print(f"✓ Index '{index_name}' already exists")
            print(f"  Details: {existing_indexes[index_name]}")
            return
        
        print(f"Creating index '{index_name}'...")
        print("  Field: fingerprint.nucleus_entity")
        print("  Type: Unique")
        print("  Options: sparse=True (allows null values)")
        print()
        
        # Create the unique index
        # sparse=True allows documents without the field or with null values
        # unique=True ensures no duplicates for non-null values
        result = await narratives_collection.create_index(
            [("fingerprint.nucleus_entity", ASCENDING)],
            name=index_name,
            unique=True,
            sparse=True,
            background=True
        )
        
        print(f"✓ Index created successfully: {result}")
        print()
        
        # Verify the index was created
        updated_indexes = await narratives_collection.index_information()
        if index_name in updated_indexes:
            print("✓ Index verification successful")
            print(f"  Index details: {updated_indexes[index_name]}")
        else:
            print("✗ Warning: Index not found in verification check")
        
        print()
        print("=" * 70)
        print("Index creation complete!")
        print("=" * 70)
        print()
        print("This index will:")
        print("  1. Prevent duplicate narratives with the same nucleus_entity")
        print("  2. Enforce uniqueness at the database level")
        print("  3. Work alongside application-level validation")
        print()
        
    except OperationFailure as e:
        if "duplicate key" in str(e).lower():
            print("✗ Error: Cannot create unique index - duplicate values exist!")
            print()
            print("This means there are narratives with duplicate nucleus_entity values.")
            print("You need to clean up duplicates before creating this index.")
            print()
            print("Suggested actions:")
            print("  1. Run: poetry run python scripts/check_duplicate_narratives.py")
            print("  2. Run: poetry run python scripts/clean_duplicate_narratives.py")
            print("  3. Re-run this script")
            sys.exit(1)
        else:
            print(f"✗ Database operation failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error creating index: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def main():
    """Main entry point."""
    await create_fingerprint_index()


if __name__ == "__main__":
    asyncio.run(main())
