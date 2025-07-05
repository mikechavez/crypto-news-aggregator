"""
Service for handling cryptocurrency price data and monitoring.
"""
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from pycoingecko import CoinGeckoAPI
from ..core.config import settings

logger = logging.getLogger(__name__)

class PriceService:
    """Service for handling cryptocurrency price data and monitoring."""
    
    def __init__(self):
        self.cg = CoinGeckoAPI()
        self.price_history: Dict[str, List[Dict]] = {}
        self.market_data: Dict[str, Any] = {}
        self.price_change_threshold = settings.PRICE_CHANGE_THRESHOLD  # Default 2% price change threshold
        self.price_check_interval = settings.PRICE_CHECK_INTERVAL  # Default 5 minutes
        
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
        # Get the latest market data which will also update our price history
        market_data = await self.get_market_data()
        
        if not market_data or 'current_price' not in market_data:
            return None
            
        current_price = market_data['current_price']
        timestamp = datetime.utcnow()
        
        # We need at least 2 data points to detect movement
        if len(self.price_history.get('bitcoin', [])) < 2:
            return None
            
        # Get the previous price point
        previous_entry = self.price_history['bitcoin'][-2]
        previous_price = previous_entry['price']
        
        # Calculate price change percentage
        price_change_pct = ((current_price - previous_price) / previous_price) * 100
        
        # Check if the movement is significant
        if abs(price_change_pct) >= self.price_change_threshold:
            return {
                'symbol': 'BTC',
                'current_price': current_price,
                'previous_price': previous_price,
                'change_pct': round(price_change_pct, 2),
                'timestamp': timestamp.isoformat(),
                'direction': 'up' if price_change_pct > 0 else 'down',
                'market_cap': market_data.get('market_cap', 0),
                'volume_24h': market_data.get('total_volume', 0)
            }
        
        return None
    
    async def get_market_data(self) -> Dict[str, Any]:
        """
        Get current market data for Bitcoin.
        
        Returns:
            Dict containing market data including price, market cap, volume, etc.
        """
        try:
            # Get detailed market data for Bitcoin
            data = self.cg.get_coin_by_id(
                id='bitcoin',
                localization=False,
                tickers=False,
                market_data=True,
                community_data=False,
                developer_data=False,
                sparkline=False
            )
            
            if not data or 'market_data' not in data:
                logger.warning("No market data available in API response")
                return {}
                
            market_data = data['market_data']
            self.market_data = {
                'current_price': market_data.get('current_price', {}).get('usd'),
                'price_change_percentage_24h': market_data.get('price_change_percentage_24h', 0),
                'market_cap': market_data.get('market_cap', {}).get('usd', 0),
                'total_volume': market_data.get('total_volume', {}).get('usd', 0),
                'high_24h': market_data.get('high_24h', {}).get('usd'),
                'low_24h': market_data.get('low_24h', {}).get('usd'),
                'last_updated': market_data.get('last_updated')
            }
            
            # Update price history with the latest data
            if 'current_price' in self.market_data:
                await self._update_price_history(
                    self.market_data['current_price'],
                    self.market_data['price_change_percentage_24h']
                )
                
            return self.market_data
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return {}
    
    async def _update_price_history(self, price: float, change_24h: float) -> None:
        """Update the price history with the latest price data."""
        timestamp = datetime.utcnow()
        price_entry = {
            'price': price,
            'timestamp': timestamp,
            'price_change_percentage_24h': change_24h
        }
        
        if 'bitcoin' not in self.price_history:
            self.price_history['bitcoin'] = []
            
        self.price_history['bitcoin'].append(price_entry)
        
        # Keep only the last 1000 price points to prevent memory issues
        if len(self.price_history['bitcoin']) > 1000:
            self.price_history['bitcoin'] = self.price_history['bitcoin'][-1000:]
    
    def get_recent_price_history(self, hours: int = 24) -> List[Dict]:
        """
        Get recent price history for Bitcoin.
        
        Args:
            hours: Number of hours of history to return (max 168 hours/7 days)
            
        Returns:
            List of price points with timestamp and price
        """
        if 'bitcoin' not in self.price_history or not self.price_history['bitcoin']:
            return []
            
        # Cap at 7 days of history for performance
        hours = min(int(hours), 168)
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            p for p in self.price_history['bitcoin']
            if p['timestamp'] > cutoff
        ]

# Singleton instance
price_service = PriceService()
