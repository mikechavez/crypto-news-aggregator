#!/usr/bin/env python3
"""
Inspect the actual structure of narrative documents in MongoDB.
"""

import asyncio
import os
from dotenv import load_dotenv
import json

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto_news_aggregator.db.mongodb import mongo_manager

# Load environment variables
load_dotenv()


async def inspect_narratives():
    """Inspect narrative document structure."""
    
    # Initialize MongoDB connection
    await mongo_manager.initialize()
    
    try:
        # Get async database
        db = await mongo_manager.get_async_database()
        narratives_collection = db.narratives
        
        # Get a few sample narratives
        cursor = narratives_collection.find({}).limit(5)
        narratives = await cursor.to_list(length=5)
        
        print("=" * 80)
        print("NARRATIVE DOCUMENT STRUCTURE INSPECTION")
        print("=" * 80)
        print()
        
        if not narratives:
            print("No narratives found in the database.")
            return
        
        for i, narrative in enumerate(narratives, 1):
            print(f"Narrative {i}:")
            print("-" * 80)
            
            # Convert ObjectId to string for JSON serialization
            if '_id' in narrative:
                narrative['_id'] = str(narrative['_id'])
            
            # Pretty print the document
            print(json.dumps(narrative, indent=2, default=str))
            print()
            print()
    
    finally:
        await mongo_manager.close()


if __name__ == '__main__':
    asyncio.run(inspect_narratives())
