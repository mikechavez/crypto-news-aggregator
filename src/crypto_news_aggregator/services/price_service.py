"""
Service for handling cryptocurrency price data and monitoring with alerting capabilities.
"""
import logging
import aiohttp
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timezone, timedelta
from ..core.config import get_settings

logger = logging.getLogger(__name__)

class CoinGeckoPriceService:
    """Service for handling cryptocurrency price data and monitoring using CoinGecko API."""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        self.session = None
        self.price_history: Dict[str, List[Dict]] = {}
        self.market_data: Dict[str, Any] = {}
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp client session."""
        if self.session is None or self.session.closed:
            settings = get_settings()
            headers = {}
            if settings.COINGECKO_API_KEY:
                # For Pro API plans, the header is x-cg-pro-api-key
                headers['x-cg-pro-api-key'] = settings.COINGECKO_API_KEY
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
        
    async def close(self):
        """Close the aiohttp client session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_bitcoin_price(self) -> Dict[str, float]:
        """
        Get current Bitcoin price and 24h change from CoinGecko.
        
        Returns:
            Dict containing 'price' (float), 'change_24h' (float), and 'timestamp' (datetime)
        """
        session = await self.get_session()
        url = f"{self.BASE_URL}/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                
                price_data = data.get('bitcoin', {})
                price = price_data.get('usd')
                change_24h = price_data.get('usd_24h_change', 0)
                
                return {
                    'price': float(price) if price is not None else None,
                    'change_24h': float(change_24h) if change_24h is not None else 0.0,
                    'timestamp': datetime.now(timezone.utc)
                }
                
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching Bitcoin price from CoinGecko: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_bitcoin_price: {e}")
            raise

    async def get_prices(self, coin_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get current prices and 24h change for a list of cryptocurrencies.

        Args:
            coin_ids: A list of CoinGecko coin IDs (e.g., ['bitcoin', 'ethereum']).

        Returns:
            A dictionary mapping each coin ID to its price data.
        """
        if not coin_ids:
            return {}

        session = await self.get_session()
        ids_str = ",".join(coin_ids)
        url = f"{self.BASE_URL}/simple/price?ids={ids_str}&vs_currencies=usd&include_24hr_change=true"

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()

                result = {}
                for coin_id, price_data in data.items():
                    price = price_data.get('usd')
                    change_24h = price_data.get('usd_24h_change', 0)
                    result[coin_id] = {
                        'price': float(price) if price is not None else None,
                        'change_24h': float(change_24h) if change_24h is not None else 0.0,
                        'timestamp': datetime.now(timezone.utc)
                    }
                return result

        except aiohttp.ClientError as e:
            logger.error(f"Error fetching prices from CoinGecko: {e}")
            return {coin_id: {} for coin_id in coin_ids} # Return empty dicts for failed coins
        except Exception as e:
            logger.error(f"Unexpected error in get_prices: {e}")
            return {coin_id: {} for coin_id in coin_ids}

    async def get_historical_prices(self, coin_id: str, days: int) -> Optional[List[Tuple[datetime, float]]]:
        """
        Get historical price data for a specific coin.

        Args:
            coin_id: The CoinGecko ID of the coin (e.g., 'bitcoin').
            days: The number of days to fetch historical data for.

        Returns:
            A list of (timestamp, price) tuples, or None if an error occurs.
        """
        session = await self.get_session()
        url = f"{self.BASE_URL}/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=daily"

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                
                prices = data.get('prices', [])
                # Convert timestamp from ms to datetime object
                return [(datetime.fromtimestamp(p[0] / 1000, tz=timezone.utc), p[1]) for p in prices]

        except aiohttp.ClientError as e:
            logger.error(f"Error fetching historical data for {coin_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_historical_prices for {coin_id}: {e}")
            return None
    
    async def calculate_price_change_percent(
        self, 
        current_price: float, 
        previous_price: float
    ) -> float:
        """
        Calculate percentage change between two prices.
        
        Args:
            current_price: Current price
            previous_price: Previous price to compare against
            
        Returns:
            float: Percentage change (can be positive or negative)
        """
        if previous_price == 0:
            return 0.0
        return ((current_price - previous_price) / previous_price) * 100
    
    async def should_trigger_alert(
        self, 
        current_price: float, 
        last_alert_price: float, 
        threshold: float
    ) -> Tuple[bool, float]:
        """
        Check if price change exceeds the specified threshold.
        
        Args:
            current_price: Current price
            last_alert_price: Price at last alert
            threshold: Percentage threshold for alert
            
        Returns:
            Tuple of (should_alert, change_percent)
        """
        if last_alert_price is None:
            return False, 0.0
            
        change_percent = await self.calculate_price_change_percent(
            current_price, last_alert_price
        )
        
        return abs(change_percent) >= threshold, change_percent
    
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
price_service = CoinGeckoPriceService()
