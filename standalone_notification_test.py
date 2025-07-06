"""
Standalone test for the notification service logic.
This file can be run directly without loading the entire project.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# Simple in-memory database for testing
class InMemoryDB:
    def __init__(self):
        self.data = {
            'alerts': [],
            'users': [],
            'articles': []
        }
    
    async def find(self, collection: str, query: Dict, limit: Optional[int] = None) -> List[Dict]:
        results = [doc for doc in self.data[collection] if self._matches(doc, query)]
        return results[:limit] if limit is not None else results
    
    async def find_one(self, collection: str, query: Dict) -> Optional[Dict]:
        for doc in self.data[collection]:
            if self._matches(doc, query):
                return doc
        return None
    
    def _matches(self, doc: Dict, query: Dict) -> bool:
        for key, value in query.items():
            if key not in doc or doc[key] != value:
                return False
        return True

# Mock MongoDB manager
class MockMongoManager:
    def __init__(self, db):
        self.db = db
    
    def get_async_collection(self, name: str):
        return self.db

# Alert conditions as strings for simplicity
ABOVE = "ABOVE"
BELOW = "BELOW"
PERCENT_UP = "PERCENT_UP"
PERCENT_DOWN = "PERCENT_DOWN"

# Notification Service with minimal dependencies
class NotificationService:
    def __init__(self, db):
        self.db = db
    
    async def process_price_alert(
        self,
        crypto_id: str,
        crypto_name: str,
        crypto_symbol: str,
        current_price: float,
        price_change_24h: float
    ) -> Dict[str, int]:
        """Process price alerts for a given cryptocurrency."""
        # Get all active alerts for this cryptocurrency
        alerts = await self.db.find('alerts', {
            'crypto_id': crypto_id,
            'is_active': True
        })
        
        result = {
            'crypto_id': crypto_id,
            'alerts_processed': 0,
            'alerts_triggered': 0,
            'notifications_sent': 0,
            'errors': 0
        }
        
        for alert_data in alerts:
            result['alerts_processed'] += 1
            
            try:
                # Use alert_data directly as a dict
                alert = alert_data
                
                # Check if alert should be triggered
                if self._check_alert_condition(alert, current_price, price_change_24h):
                    result['alerts_triggered'] += 1
                    
                    # Send notification
                    success = await self._send_alert_notification(
                        alert=alert,
                        crypto_name=crypto_name,
                        crypto_symbol=crypto_symbol,
                        current_price=current_price,
                        price_change_24h=price_change_24h
                    )
                    
                    if success:
                        result['notifications_sent'] += 1
                    else:
                        result['errors'] += 1
                        
                    # Update last_triggered
                    alert['last_triggered'] = datetime.utcnow()
                    # In a real implementation, we would save this back to the database
                    
            except Exception as e:
                print(f"Error processing alert {alert_data.get('id')}: {e}")
                result['errors'] += 1
        
        return result
    
    def _check_alert_condition(
        self,
        alert: Dict,
        current_price: float,
        price_change_24h: float
    ) -> bool:
        """Check if an alert condition is met."""
        condition = alert.get('condition')
        threshold = alert.get('threshold', 0.0)
        
        if condition == 'ABOVE':
            return current_price > threshold
        elif condition == 'BELOW':
            return current_price < threshold
        elif condition == 'PERCENT_UP':
            return price_change_24h > threshold
        elif condition == 'PERCENT_DOWN':
            return price_change_24h < -threshold
        
        return False
    
    async def _send_alert_notification(
        self,
        alert: Dict,
        crypto_name: str,
        crypto_symbol: str,
        current_price: float,
        price_change_24h: float
    ) -> bool:
        """Send a price alert notification with news context."""
        try:
            # Get user details
            user = await self.db.find_one('users', {'_id': alert['user_id']})
            if not user:
                print(f"User {alert['user_id']} not found")
                return False
            
            # Get relevant news articles
            news_articles = await self._get_recent_news(crypto_name, limit=3)
            
            # In a real implementation, we would send an email here
            print(f"\n=== Price Alert ===")
            print(f"To: {user['email']}")
            print(f"Subject: {crypto_name} Price Alert - {current_price:.2f} {crypto_symbol}")
            print(f"\nHello {user.get('name', 'there')},")
            print(f"\nThe price of {crypto_name} is now {current_price:.2f} {crypto_symbol}.")
            print(f"24h change: {price_change_24h:+.2f}%")
            
            if news_articles:
                print("\nRecent news:")
                for i, article in enumerate(news_articles, 1):
                    print(f"{i}. {article['title']} - {article['source']['name']}")
                    print(f"   {article['url']}\n")
            
            print("\nManage your alerts: [URL to alert settings]")
            print("==================\n")
            
            return True
            
        except Exception as e:
            print(f"Error sending notification: {e}")
            return False
    
    async def _get_recent_news(self, crypto_name: str, limit: int = 3) -> List[Dict]:
        """Get recent news articles related to a cryptocurrency."""
        # In a real implementation, this would query the database
        # For testing, we'll just return some mock data
        return await self.db.find('articles', {
            '$or': [
                {'title': {'$regex': crypto_name, '$options': 'i'}},
                {'content': {'$regex': crypto_name, '$options': 'i'}},
                {'tags': {'$in': [crypto_name]}}
            ]
        }, limit=limit)

# Test data
def setup_test_data(db):
    # Add a test user
    user_id = "user123"
    db.data['users'].append({
        '_id': user_id,
        'email': 'test@example.com',
        'name': 'Test User'
    })
    
    # Add test alerts
    db.data['alerts'].extend([
        {
            'id': 'alert1',
            'user_id': user_id,
            'crypto_id': 'bitcoin',
            'condition': 'ABOVE',  # Store as string
            'threshold': 50000.0,
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(days=1),
            'last_triggered': None
        },
        {
            'id': 'alert2',
            'user_id': user_id,
            'crypto_id': 'ethereum',
            'condition': 'BELOW',  # Store as string
            'threshold': 3000.0,
            'is_active': True,
            'created_at': datetime.utcnow() - timedelta(hours=1),
            'last_triggered': None
        }
    ])
    
    # Add test news articles
    db.data['articles'].extend([
        {
            'id': 'news1',
            'title': 'Bitcoin Reaches New All-Time High',
            'source': {'name': 'Crypto News'},
            'url': 'https://example.com/btc-news',
            'published_at': datetime.utcnow() - timedelta(hours=2),
            'description': 'Bitcoin has reached a new all-time high price of $50,000.',
            'tags': ['bitcoin', 'price']
        },
        {
            'id': 'news2',
            'title': 'Institutional Investors Flock to Bitcoin',
            'source': {'name': 'Crypto Insights'},
            'url': 'https://example.com/btc-institutional',
            'published_at': datetime.utcnow() - timedelta(hours=1),
            'description': 'Major institutions are increasing their Bitcoin holdings.',
            'tags': ['bitcoin', 'institutional']
        },
        {
            'id': 'news3',
            'title': 'Ethereum 2.0 Launches Successfully',
            'source': {'name': 'Crypto Today'},
            'url': 'https://example.com/eth2-launch',
            'published_at': datetime.utcnow() - timedelta(hours=3),
            'description': 'Ethereum has successfully transitioned to proof-of-stake.',
            'tags': ['ethereum', 'upgrade']
        }
    ])

# Test the notification service
async def test_notification_service():
    print("=== Starting Notification Service Test ===")
    
    # Setup in-memory database
    db = InMemoryDB()
    setup_test_data(db)
    
    # Create notification service
    service = NotificationService(db)
    
    # Test price alert for Bitcoin
    print("\nTesting Bitcoin price alert...")
    result = await service.process_price_alert(
        crypto_id='bitcoin',
        crypto_name='Bitcoin',
        crypto_symbol='BTC',
        current_price=51000.0,
        price_change_24h=5.5
    )
    print(f"\nBitcoin alert result: {result}")
    
    # Test price alert for Ethereum
    print("\nTesting Ethereum price alert...")
    result = await service.process_price_alert(
        crypto_id='ethereum',
        crypto_name='Ethereum',
        crypto_symbol='ETH',
        current_price=2900.0,
        price_change_24h=-2.5
    )
    print(f"\nEthereum alert result: {result}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_notification_service())
