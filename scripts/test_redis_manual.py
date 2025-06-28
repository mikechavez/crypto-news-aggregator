"""
Test script to manually verify Redis connection with hardcoded values.
WARNING: This is for testing purposes only. Never commit sensitive data to version control.
"""
import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('redis_manual_test')

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, os.path.join(project_root, 'src'))

# Import after path setup
from crypto_news_aggregator.core.redis_rest_client import RedisRESTClient

def test_manual_connection(redis_url, redis_token):
    """Test Redis connection with provided credentials."""
    try:
        logger.info("=== Testing Redis Connection ===")
        logger.info(f"Using URL: {redis_url}")
        
        # Create client with provided credentials
        client = RedisRESTClient(base_url=redis_url, token=redis_token)
        
        # Test ping
        logger.info("Testing ping...")
        if client.ping():
            logger.info("✅ Ping successful")
            return True
        else:
            logger.error("❌ Ping failed - No response from server")
            return False
            
    except Exception as e:
        logger.error(f"❌ Connection failed with error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Replace these with your actual Upstash Redis credentials
    UPSTASH_REDIS_REST_URL = input("Enter your Upstash Redis REST URL: ").strip()
    UPSTASH_REDIS_TOKEN = input("Enter your Upstash Redis token: ").strip()
    
    logger.info("Starting manual Redis connection test...")
    success = test_manual_connection(UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_TOKEN)
    
    if success:
        logger.info("✅ Connection test successful!")
    else:
        logger.error("❌ Connection test failed. Please check your credentials and network connection.")
    
    input("Press Enter to exit...")
