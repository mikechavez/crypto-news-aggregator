"""
Service for storing and retrieving historical price data.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from bson import ObjectId

from ..db.mongodb import mongo_manager, COLLECTION_PRICE_HISTORY
from ..core.config import get_settings

logger = logging.getLogger(__name__)
# settings = get_settings()  # Removed top-level settings; use lazy initialization in methods as needed.

class PriceHistoryService:
    """Service for managing cryptocurrency price history."""
    
    def __init__(self):
        self.collection_name = COLLECTION_PRICE_HISTORY
    
    async def _get_collection(self) -> Any:
        """Get the MongoDB collection for price history."""
        if not hasattr(self, '_collection'):
            self._collection = await mongo_manager.get_async_collection(self.collection_name)
        return self._collection
    
    async def store_price(
        self, 
        cryptocurrency: str, 
        price: float, 
        change_24h: float
    ) -> str:
        """
        Store a new price data point.
        
        Args:
            cryptocurrency: Cryptocurrency symbol (e.g., 'bitcoin')
            price: Current price in USD
            change_24h: 24-hour price change percentage
            
        Returns:
            str: ID of the inserted document
        """
        collection = await self._get_collection()
        price_doc = {
            'cryptocurrency': cryptocurrency.lower(),
            'price_usd': price,
            'change_24h_percent': change_24h,
            'timestamp': datetime.now(timezone.utc)
        }
        
        result = await collection.insert_one(price_doc)
        return str(result.inserted_id)
    
    async def get_latest_price(self, cryptocurrency: str = 'bitcoin') -> Optional[Dict]:
        """
        Get the most recent price record for a cryptocurrency.
        
        Args:
            cryptocurrency: Cryptocurrency symbol (default: 'bitcoin')
            
        Returns:
            Optional[Dict]: Latest price data or None if not found
        """
        collection = await self._get_collection()
        latest = await collection.find_one(
            {"cryptocurrency": cryptocurrency.lower()},
            sort=[("timestamp", -1)]
        )
        
        if latest and '_id' in latest:
            latest['id'] = str(latest.pop('_id'))
            return latest
        return None
    
    async def get_price_history(
        self, 
        cryptocurrency: str = 'bitcoin',
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get historical price data for a cryptocurrency.
        
        Args:
            cryptocurrency: Cryptocurrency symbol (default: 'bitcoin')
            hours: Number of hours of history to retrieve (default: 24)
            limit: Maximum number of records to return (default: 100)
            
        Returns:
            List[Dict]: List of price records
        """
        collection = await self._get_collection()
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        cursor = collection.find({
            "cryptocurrency": cryptocurrency.lower(),
            "timestamp": {"$gte": since}
        }).sort("timestamp", -1).limit(limit)
        
        history = []
        async for doc in cursor:
            doc['id'] = str(doc.pop('_id'))
            history.append(doc)
            
        return history
    
    async def get_price_change(
        self, 
        cryptocurrency: str = 'bitcoin',
        hours: int = 24
    ) -> Dict[str, float]:
        """
        Calculate price change over a specified time period.
        
        Args:
            cryptocurrency: Cryptocurrency symbol (default: 'bitcoin')
            hours: Time period in hours (default: 24)
            
        Returns:
            Dict with price change information
        """
        collection = await self._get_collection()
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Get oldest price in the period
        oldest_cursor = collection.find(
            {"cryptocurrency": cryptocurrency.lower(), "timestamp": {"$gte": since}},
            sort=[("timestamp", 1)],
            limit=1
        )
        
        # Get latest price
        latest = await collection.find_one(
            {"cryptocurrency": cryptocurrency.lower()},
            sort=[("timestamp", -1)]
        )
        
        oldest = await oldest_cursor.to_list(length=1)
        oldest = oldest[0] if oldest else None
        
        if not latest or not oldest:
            return {
                'change_percent': 0.0,
                'start_price': 0.0,
                'end_price': 0.0,
                'hours': hours
            }
            
        start_price = oldest.get('price_usd', 0)
        end_price = latest.get('price_usd', 0)
        change_percent = ((end_price - start_price) / start_price * 100) if start_price > 0 else 0
        
        return {
            'change_percent': round(change_percent, 2),
            'start_price': start_price,
            'end_price': end_price,
            'hours': hours
        }


# Singleton instance
price_history_service = PriceHistoryService()
