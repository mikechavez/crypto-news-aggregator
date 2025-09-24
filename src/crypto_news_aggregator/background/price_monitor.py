"""
Service for monitoring cryptocurrency prices and triggering alerts with article context.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..services.price_service import price_service
from ..services.notification_service import get_notification_service
from ..services.article_service import article_service

logger = logging.getLogger(__name__)

class PriceMonitor:
    """Monitors cryptocurrency prices and triggers alerts with relevant article context."""
    
    def __init__(self, check_interval: int = 300):
        """Initialize the price monitor.
        
        Args:
            check_interval: How often to check prices, in seconds (default: 300s/5min)
        """
        self.check_interval = check_interval
        self.is_running = False
        self.article_lookback_hours = 6  # Lookback window for relevant articles
        self.min_relevance_score = 0.3  # Minimum score for articles to be included
        
    async def start(self) -> None:
        """Start the price monitoring service."""
        if self.is_running:
            logger.warning("Price monitor is already running")
            return
            
        self.is_running = True
        logger.info("Starting price monitor")
        
        # Initial price fetch to populate history
        await price_service.get_market_data()
        
        # Start the monitoring loop
        while self.is_running:
            try:
                await self.check_prices()
            except Exception as e:
                logger.error(f"Error in price monitoring loop: {e}")
                
            # Wait for the next check interval
            await asyncio.sleep(self.check_interval)
    
    async def stop(self) -> None:
        """Stop the price monitoring service."""
        self.is_running = False
        logger.info("Stopping price monitor")
    
    async def check_prices(self) -> None:
        """Check prices and trigger alerts if conditions are met."""
        try:
            # Get the latest market data
            market_data = await price_service.get_market_data()
            if not market_data or 'current_price' not in market_data:
                logger.warning("No price data available")
                return
                
            current_price = market_data['current_price']
            price_change_24h = market_data.get('price_change_percentage_24h', 0)
            
            logger.debug(
                f"Checking prices - BTC: ${current_price:,.2f} "
                f"({price_change_24h:+.2f}% 24h)"
            )
            
            # Get relevant articles for context
            context_articles = []
            if abs(price_change_24h) >= 1.0:  # Only fetch articles for significant movements
                context_articles = await self._get_price_context(price_change_24h)
            
            # Process alerts for Bitcoin
            async for db in get_session():
                notification_service = get_notification_service()
                result = await notification_service.process_price_alert(
                    db=db,
                    crypto_id='bitcoin',
                    crypto_name='Bitcoin',
                    crypto_symbol='BTC',
                    current_price=current_price,
                    price_change_24h=price_change_24h,
                    context_articles=context_articles
                )
            
            logger.info(
                f"Processed {result['alerts_processed']} alerts: "
                f"{result['alerts_triggered']} triggered, "
                f"{result['notifications_sent']} notifications sent, "
                f"{len(context_articles)} relevant articles included"
            )
            
        except Exception as e:
            logger.error(f"Error checking prices: {e}")
            raise
    
    async def _get_price_context(self, price_change: float) -> List[Dict[str, Any]]:
        """
        Get articles that might explain the price movement.
        
        Args:
            price_change: The percentage price change
            
        Returns:
            List of relevant articles with relevance scores
        """
        try:
            # Get recent articles
            start_date = datetime.utcnow() - timedelta(hours=self.article_lookback_hours)
            recent_articles, _ = await article_service.list_articles(
                start_date=start_date,
                limit=20
            )
            
            # Score articles for relevance
            scored_articles = []
            for article in recent_articles:
                score = self._score_article_relevance(article, price_change)
                if score >= self.min_relevance_score:
                    scored_articles.append({
                        'article': article,
                        'score': score,
                        'title': article.title,
                        'source': article.source,
                        'url': getattr(article, 'url', ''),
                        'published_at': article.published_at.isoformat() if hasattr(article, 'published_at') else None,
                        'snippet': getattr(article, 'content', '')[:200] + '...' if hasattr(article, 'content') else ''
                    })
            
            # Return top 5 most relevant articles
            scored_articles.sort(key=lambda x: x['score'], reverse=True)
            return scored_articles[:5]
            
        except Exception as e:
            logger.error(f"Error getting price context: {e}")
            return []
    
    def _score_article_relevance(self, article: Any, price_change: float) -> float:
        """
        Score an article's relevance to a price change.
        
        Args:
            article: The article to score
            price_change: The percentage price change
            
        Returns:
            Relevance score between 0 and 1
        """
        score = 0.0
        
        # Check for Bitcoin/crypto keywords in title and content
        keywords = ['bitcoin', 'btc', 'crypto', 'price', 'market', 'bull', 'bear', 'rally', 'plunge', 'surge', 'drop']
        title_lower = article.title.lower() if hasattr(article, 'title') else ''
        content_lower = (getattr(article, 'content', '') or '').lower()
        
        # Check for price direction keywords
        if price_change > 0:
            keywords.extend(['up', 'rise', 'increase', 'gain', 'rally'])
        else:
            keywords.extend(['down', 'fall', 'decrease', 'loss', 'drop', 'plunge'])
        
        # Score based on keyword matches
        for keyword in set(keywords):  # Use set to avoid duplicate keywords
            if keyword in title_lower:
                score += 0.2
            if keyword in content_lower:
                score += 0.05  # Lower weight for content matches
        
        # Boost for very recent articles (last 2 hours)
        if hasattr(article, 'published_at'):
            article_age = (datetime.utcnow() - article.published_at).total_seconds() / 3600
            if article_age < 2:
                score += 0.3
            elif article_age < 6:
                score += 0.1
        
        # Cap score at 1.0
        return min(score, 1.0)

# Singleton instance
price_monitor = PriceMonitor()

# For testing
def run_monitor():
    """Run the price monitor (for testing purposes)."""
    import asyncio
    import signal
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Enable debug logging for our package
    logging.getLogger("crypto_news_aggregator").setLevel(logging.DEBUG)
    
    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Handle graceful shutdown
    def shutdown():
        logger.info("Shutting down...")
        loop.create_task(price_monitor.stop())
        
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)
    
    try:
        # Start the monitor
        logger.info("Starting price monitor (press Ctrl+C to stop)")
        loop.run_until_complete(price_monitor.start())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.exception("Error in price monitor:")
    finally:
        # Cleanup
        pending = asyncio.all_tasks(loop=loop)
        for task in pending:
            task.cancel()
        
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        
        loop.close()
        logger.info("Price monitor stopped")

if __name__ == "__main__":
    run_monitor()
