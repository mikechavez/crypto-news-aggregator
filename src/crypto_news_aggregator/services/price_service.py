"""
Service for handling cryptocurrency price data and monitoring.
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from pycoingecko import CoinGeckoAPI

logger = logging.getLogger(__name__)

class PriceService:
    """Service for handling cryptocurrency price data and monitoring."""
    
    def __init__(self):
        self.cg = CoinGeckoAPI()
        self.price_history: Dict[str, List[Dict]] = {}
        self.price_change_threshold = 3.0  # 3% price change threshold
        self.price_check_interval = 300  # 5 minutes in seconds
        
    async def get_bitcoin_price(self) -> Optional[float]:
        """Get the current Bitcoin price in USD."""
        try:
            price_data = self.cg.get_price(ids='bitcoin', vs_currencies='usd')
            return price_data.get('bitcoin', {}).get('usd')
        except Exception as e:
            logger.error(f"Error fetching Bitcoin price: {e}")
            return None
    
    async def check_price_movement(self) -> Optional[Dict]:
        """
        Check for significant price movements.
        
        Returns:
            Dict with movement details if significant, None otherwise
        """
        current_price = await self.get_bitcoin_price()
        if current_price is None:
            return None
            
        timestamp = datetime.utcnow()
        price_entry = {'price': current_price, 'timestamp': timestamp}
        
        # Store price in history
        if 'bitcoin' not in self.price_history:
            self.price_history['bitcoin'] = []
        self.price_history['bitcoin'].append(price_entry)
        
        # Keep only recent history (last hour)
        cutoff = timestamp - timedelta(hours=1)
        self.price_history['bitcoin'] = [
            p for p in self.price_history['bitcoin'] 
            if p['timestamp'] > cutoff
        ]
        
        # Check for significant movement if we have enough history
        if len(self.price_history['bitcoin']) > 1:
            previous_price = self.price_history['bitcoin'][-2]['price']
            price_change_pct = ((current_price - previous_price) / previous_price) * 100
            
            if abs(price_change_pct) >= self.price_change_threshold:
                return {
                    'symbol': 'BTC',
                    'current_price': current_price,
                    'previous_price': previous_price,
                    'change_pct': round(price_change_pct, 2),
                    'timestamp': timestamp.isoformat(),
                    'direction': 'up' if price_change_pct > 0 else 'down'
                }
        
        return None
    
    def get_recent_price_history(self, hours: int = 24) -> List[Dict]:
        """Get recent price history for Bitcoin."""
        if 'bitcoin' not in self.price_history:
            return []
            
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            p for p in self.price_history['bitcoin']
            if p['timestamp'] > cutoff
        ]

# Singleton instance
price_service = PriceService()
