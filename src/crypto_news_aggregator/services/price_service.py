"""
Service for handling cryptocurrency price data and monitoring with alerting capabilities.
"""
import logging
import aiohttp
import asyncio
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from aiocache import caches, cached
from ..core.config import get_settings
import random
import numpy as np

# Configure a simple in-memory cache
# In a production environment, you might want to use RedisCache or MemcachedCache
caches.set_config({
    'default': {
        'cache': "aiocache.SimpleMemoryCache",
        'serializer': {
            'class': "aiocache.serializers.StringSerializer"
        }
    }
})

# --- MOCK DATA --- #
def _generate_mock_market_data(coin_id: str) -> Dict[str, Any]:
    """Generates detailed mock market data for a given coin ID."""
    base_prices = {'bitcoin': 60000, 'ethereum': 2000}
    base_price = base_prices.get(coin_id, 100)

    return {
        'id': coin_id,
        'name': coin_id.capitalize(),
        'current_price': base_price * (1 + random.uniform(-0.05, 0.05)),
        'market_cap_rank': 1 if coin_id == 'bitcoin' else 2 if coin_id == 'ethereum' else 100,
        'price_change_percentage_1h_in_currency': random.uniform(-1, 1),
        'price_change_percentage_24h_in_currency': random.uniform(-5, 5),
        'price_change_percentage_7d_in_currency': random.uniform(-10, 10),
        'total_volume': random.uniform(1e9, 5e10),
        'market_cap': base_price * 21000000 if coin_id == 'bitcoin' else base_price * 120000000,
    }

def _generate_mock_price(coin_id: str) -> Dict[str, Any]:
    """Generates mock price data for a given coin ID."""
    base_price = {
        'bitcoin': 60000,
        'ethereum': 2000,
    }.get(coin_id.lower(), 100)
    
    price = base_price * (1 + random.uniform(-0.05, 0.05))
    change_24h = random.uniform(-5, 5)
    
    return {
        'price': price,
        'change_24h': change_24h,
        'timestamp': datetime.now(timezone.utc)
    }

# --- API Usage Counter ---
API_CALL_COUNTER = {
    'count': 0,
    'last_reset': datetime.now(timezone.utc)
}
MONTHLY_API_LIMIT = 10000
WARNING_THRESHOLD = 0.8  # 80% of the limit

def increment_api_call_counter():
    """Increments the API call counter and logs a warning if the usage is high."""
    now = datetime.now(timezone.utc)
    # Reset counter monthly
    if (now - API_CALL_COUNTER['last_reset']).days > 30:
        API_CALL_COUNTER['count'] = 0
        API_CALL_COUNTER['last_reset'] = now

    API_CALL_COUNTER['count'] += 1
    usage_percent = (API_CALL_COUNTER['count'] / MONTHLY_API_LIMIT) * 100

    if usage_percent >= WARNING_THRESHOLD * 100:
        logger.warning(
            f"CoinGecko API usage is at {usage_percent:.2f}% of the monthly limit. "
            f"({API_CALL_COUNTER['count']}/{MONTHLY_API_LIMIT})"
        )
    logger.debug(f"CoinGecko API calls: {API_CALL_COUNTER['count']}")

logger = logging.getLogger(__name__)

class CoinGeckoPriceService:
    """Service for handling cryptocurrency price data and monitoring using CoinGecko API."""

    def __init__(self):
        self.settings = get_settings()
        self._configure_endpoints()
        self.session = None
        self.price_history: Dict[str, List[Dict]] = {}
        self.market_data: Dict[str, Any] = {}

    def _configure_endpoints(self):
        """Sets the base URL based on the presence of an API key."""
        # Forcing public endpoint as the key is a demo key.
        self.BASE_URL = "https://api.coingecko.com/api/v3"
        if self.settings.coingecko_api_key:
            logger.info("CoinGecko API key found. Using Public endpoint for Demo key.")
        else:
            logger.info("No CoinGecko API key found. Using Public endpoint.")

    def reinitialize(self):
        """Re-initializes the service with the latest settings."""
        logger.info("Re-initializing CoinGeckoPriceService with latest settings.")
        get_settings.cache_clear()  # Clear the cache for the settings function
        self.settings = get_settings()
        self._configure_endpoints()
        # The session will be recreated automatically on the next API call
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp client session."""
        if self.session is None or self.session.closed:
            # Demo API key does not require a header. The key is identified by the account.
            # For a real Pro plan, the header logic would need to be restored.
            self.session = aiohttp.ClientSession()
        return self.session
        
    def _get_url_with_api_key(self, url: str) -> str:
        """Appends the CoinGecko API key as a query parameter if it exists."""
        if self.settings.coingecko_api_key:
            # For Demo plan, key is sent as a query param to the public endpoint
            separator = '&' if '?' in url else '?'
            return f"{url}{separator}x_cg_demo_api_key={self.settings.coingecko_api_key}"
        return url

    async def close(self):
        """Close the aiohttp client session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    @cached(ttl=300) # Cache for 5 minutes
    async def get_bitcoin_price(self) -> Dict[str, float]:
        """
        Get current Bitcoin price and 24h change from CoinGecko.
        
        Returns:
            Dict containing 'price' (float), 'change_24h' (float), and 'timestamp' (datetime)
        """
        if self.settings.TESTING_MODE:
            logger.info("TESTING_MODE enabled. Returning mock Bitcoin price.")
            return _generate_mock_price('bitcoin')

        increment_api_call_counter()
        session = await self.get_session()
        base_url = f"{self.BASE_URL}/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        url = self._get_url_with_api_key(base_url)

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

    @cached(ttl=300) # Cache for 5 minutes
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

        if self.settings.TESTING_MODE:
            logger.info(f"TESTING_MODE enabled. Returning mock prices for: {coin_ids}")
            return {coin_id: _generate_mock_price(coin_id) for coin_id in coin_ids}

        increment_api_call_counter()
        session = await self.get_session()
        ids_str = ",".join(coin_ids)
        base_url = f"{self.BASE_URL}/simple/price?ids={ids_str}&vs_currencies=usd&include_24hr_change=true"
        url = self._get_url_with_api_key(base_url)

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

    @cached(ttl=300) # Cache for 5 minutes
    async def get_markets_data(self, coin_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed market data for a list of cryptocurrencies.

        Args:
            coin_ids: A list of CoinGecko coin IDs (e.g., ['bitcoin', 'ethereum']).

        Returns:
            A dictionary mapping each coin ID to its market data.
        """
        if not coin_ids:
            return {}

        if self.settings.TESTING_MODE:
            logger.info(f"TESTING_MODE enabled. Returning mock market data for: {coin_ids}")
            return {coin_id: _generate_mock_market_data(coin_id) for coin_id in coin_ids}

        increment_api_call_counter()
        session = await self.get_session()
        ids_str = ",".join(coin_ids)
        price_change_params = "1h,24h,7d"
        base_url = f"{self.BASE_URL}/coins/markets?vs_currency=usd&ids={ids_str}&price_change_percentage={price_change_params}"
        url = self._get_url_with_api_key(base_url)

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()

                result = {item['id']: item for item in data}
                return result

        except aiohttp.ClientError as e:
            logger.error(f"Error fetching market data from CoinGecko: {e}")
            return {coin_id: {} for coin_id in coin_ids}
        except Exception as e:
            logger.error(f"Unexpected error in get_markets_data: {e}")
            return {coin_id: {} for coin_id in coin_ids}

    @cached(ttl=300) # Cache for 5 minutes
    async def get_historical_prices(self, coin_id: str, days: int) -> Optional[Dict[str, List[Tuple[datetime, float]]]]:
        """
        Get historical price and volume data for a specific coin.

        Args:
            coin_id: The CoinGecko ID of the coin (e.g., 'bitcoin').
            days: The number of days to fetch historical data for.

        Returns:
            A dictionary with 'prices' and 'volumes', each a list of (timestamp, value) tuples, or None if an error occurs.
        """
        if self.settings.TESTING_MODE:
            logger.info(f"TESTING_MODE enabled. Returning mock historical prices for: {coin_id}")
            mock_prices = []
            for i in range(days):
                date = datetime.now(timezone.utc) - timedelta(days=i)
                mock_data = _generate_mock_price(coin_id)
                mock_prices.append((date, mock_data['price']))
            # Mock volume data as well
            mock_volumes = [(p[0], random.uniform(1e9, 5e10)) for p in mock_prices]
            return {'prices': list(reversed(mock_prices)), 'volumes': list(reversed(mock_volumes))}

        increment_api_call_counter()
        session = await self.get_session()
        base_url = f"{self.BASE_URL}/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
        url = self._get_url_with_api_key(base_url)

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                
                prices = data.get('prices', [])
                volumes = data.get('total_volumes', [])
                
                # Convert timestamp from ms to datetime object
                price_data = [(datetime.fromtimestamp(p[0] / 1000, tz=timezone.utc), p[1]) for p in prices]
                volume_data = [(datetime.fromtimestamp(v[0] / 1000, tz=timezone.utc), v[1]) for v in volumes]
                
                return {'prices': price_data, 'volumes': volume_data}

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
    
    @cached(ttl=300) # Cache for 5 minutes
    async def get_market_data(self) -> Dict[str, Any]:
        """
        Get current market data for Bitcoin.
        
        Returns:
            Dict containing market data including price, market cap, volume, etc.
        """
        if self.settings.TESTING_MODE:
            logger.info("TESTING_MODE enabled. Returning mock market data.")
            mock_price_data = _generate_mock_price('bitcoin')
            return {
                'current_price': mock_price_data['price'],
                'price_change_percentage_24h': mock_price_data['change_24h'],
                'market_cap': 1.2e12, # Mock value
                'total_volume': 5e10, # Mock value
                'high_24h': mock_price_data['price'] * 1.05,
                'low_24h': mock_price_data['price'] * 0.95,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
        
        increment_api_call_counter()
        session = await self.get_session()
        base_url = f"{self.BASE_URL}/coins/bitcoin?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
        url = self._get_url_with_api_key(base_url)

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
            
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

    @cached(ttl=600) # Cache for 10 minutes
    async def get_global_market_data(self) -> Dict[str, Any]:
        """
        Get global cryptocurrency market data, including market cap, volume, and BTC dominance.
        
        Returns:
            Dict containing global market data.
        """
        if self.settings.TESTING_MODE:
            logger.info("TESTING_MODE enabled. Returning mock global market data.")
            return {
                'total_market_cap': {'usd': 2.5e12},
                'total_volume': {'usd': 1.5e11},
                'market_cap_percentage': {'btc': 45.0, 'eth': 18.0}
            }

        increment_api_call_counter()
        session = await self.get_session()
        base_url = f"{self.BASE_URL}/global"
        url = self._get_url_with_api_key(base_url)

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('data', {})
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching global market data from CoinGecko: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error in get_global_market_data: {e}")
            return {}

    def _get_trend_momentum_commentary(self, price_1h: float, price_24h: float, price_7d: float) -> Tuple[str, str]:
        """Analyzes multi-timeframe data to identify trend and momentum."""
        # Trend Analysis
        if price_1h > 0 and price_24h > 0 and price_7d > 0:
            trend = "strong bullish momentum"
        elif price_1h < 0 and price_24h < 0 and price_7d < 0:
            trend = "strong bearish momentum"
        elif price_1h > 0 and price_24h > 0 and price_7d < 0:
            trend = "a potential bullish reversal"
        elif price_1h < 0 and price_24h < 0 and price_7d > 0:
            trend = "a potential bearish reversal"
        elif abs(price_24h) < 1:
            trend = "a consolidation phase"
        else:
            trend = "mixed signals"

        # Momentum Indicator
        if abs(price_24h) > 5:
            momentum = "high"
        elif abs(price_24h) > 2:
            momentum = "moderate"
        else:
            momentum = "low"

        return trend, momentum

    async def generate_market_analysis_commentary(self, coin_id: str = 'bitcoin') -> str:
        """
        Generates sophisticated market analysis commentary for a given cryptocurrency.

        Args:
            coin_id: The CoinGecko ID of the coin (e.g., 'bitcoin').

        Returns:
            A string containing detailed market analysis.
        """
        # 1. Fetch detailed market data for the specified coin and top competitor (ETH)
        target_coin_id = coin_id.lower()
        competitor_coin_id = 'ethereum' if target_coin_id == 'bitcoin' else 'bitcoin'
        
        market_data_list = await self.get_markets_data([target_coin_id, competitor_coin_id])
        target_data = market_data_list.get(target_coin_id)
        competitor_data = market_data_list.get(competitor_coin_id)

        if not target_data:
            return f"Could not retrieve market data for {coin_id.capitalize()}."

        # 2. Fetch global market data for context
        global_data = await self.get_global_market_data()
        btc_dominance = global_data.get('market_cap_percentage', {}).get('btc', 0)

        # 3. Extract key metrics
        coin_name = target_data.get('name', coin_id.capitalize())
        market_cap_rank = target_data.get('market_cap_rank', 'N/A')
        price_1h = target_data.get('price_change_percentage_1h_in_currency', 0) or 0
        price_24h = target_data.get('price_change_percentage_24h_in_currency', 0) or 0
        price_7d = target_data.get('price_change_percentage_7d_in_currency', 0) or 0

        # 4. Fetch and Process Historical Data
        historical_data = await self.get_historical_prices(target_coin_id, days=7)
        volatility = 'N/A'
        avg_7d_volume = 0

        if historical_data:
            prices_7d = historical_data.get('prices', [])
            volumes_7d = historical_data.get('volumes', [])

            if prices_7d and len(prices_7d) > 1:
                daily_returns = np.diff([p[1] for p in prices_7d]) / [p[1] for p in prices_7d][:-1]
                daily_volatility = np.std(daily_returns)
                volatility = f"{daily_volatility * np.sqrt(365) * 100:.2f}%"

            if volumes_7d:
                avg_7d_volume = np.mean([v[1] for v in volumes_7d])

        # 5. Volatility and Volume Analysis
        high_24h = target_data.get('high_24h', 0)
        low_24h = target_data.get('low_24h', 0)
        intraday_volatility = 0
        if low_24h and high_24h and low_24h > 0:
            intraday_volatility = ((high_24h - low_24h) / low_24h) * 100

        total_volume = target_data.get('total_volume', 0)
        volume_text = ""
        if total_volume > 0 and avg_7d_volume > 0:
            volume_diff_percent = ((total_volume - avg_7d_volume) / avg_7d_volume) * 100
            if volume_diff_percent > 25:
                volume_desc = f"{volume_diff_percent:.0f}% above its 7-day average"
            elif volume_diff_percent < -25:
                volume_desc = f"{abs(volume_diff_percent):.0f}% below its 7-day average"
            else:
                volume_desc = "in line with its 7-day average"
            volume_text = f"Current 24h volume (${total_volume:,.0f}) is {volume_desc}. "

        # 6. Comparative Analysis
        market_avg_24h_change = global_data.get('market_cap_change_percentage_24h_usd', 0)
        market_comparison = ""
        if market_avg_24h_change:
            performance_diff = price_24h - market_avg_24h_change
            if performance_diff > 0.1:
                market_comparison = f"outperforming the broader market by {performance_diff:.2f}%. "
            else:
                market_comparison = f"underperforming the broader market by {abs(performance_diff):.2f}%. "

        # 7. Generate Professional Commentary
        current_price = target_data.get('current_price', 0)
        trend, _ = self._get_trend_momentum_commentary(price_1h, price_24h, price_7d)

        commentary = (
            f"{coin_name} (Rank #{market_cap_rank}) is trading at ${current_price:,.2f}. "
            f"It shows {trend} with price movements of 1h: {price_1h:+.2f}%, 24h: {price_24h:+.2f}%, and 7d: {price_7d:+.2f}%. "
            f"{market_comparison}"
            f"{volume_text}"
            f"Intraday volatility is {intraday_volatility:.2f}%, with an estimated 7-day annualized volatility of {volatility}. "
        )

        if target_coin_id == 'bitcoin' and btc_dominance > 0:
            commentary += f"Bitcoin's market dominance stands at {btc_dominance:.2f}%. "

        return commentary.strip()


# Factory function for dependency injection
@lru_cache()
def get_price_service() -> CoinGeckoPriceService:
    """Factory function to get a singleton instance of the price service."""
    return CoinGeckoPriceService()

price_service = get_price_service()


