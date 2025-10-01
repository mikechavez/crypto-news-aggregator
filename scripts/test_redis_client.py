import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.crypto_news_aggregator.core.redis_rest_client import RedisRESTClient
from src.crypto_news_aggregator.core.config import Settings


def test_redis_client():
    # Initialize settings
    settings = Settings()

    # Create client with settings
    client = RedisRESTClient(
        base_url=settings.UPSTASH_REDIS_REST_URL, token=settings.UPSTASH_REDIS_TOKEN
    )

    print(f"Testing connection to: {settings.UPSTASH_REDIS_REST_URL}")

    # Test ping
    if client.ping():
        print("✅ Successfully connected to Redis via REST API")
    else:
        print("❌ Failed to connect to Redis via REST API")
        return

    # Test set/get
    test_key = "test:integration"
    test_value = "test_value_123"

    # Set value
    if client.set(test_key, test_value):
        print(f"✅ Successfully set test key: {test_key}")
    else:
        print("❌ Failed to set test key")
        return

    # Get value
    retrieved = client.get(test_key)
    if retrieved == test_value:
        print(f"✅ Successfully retrieved test value: {retrieved}")
    else:
        print(f"❌ Failed to retrieve test value. Got: {retrieved}")

    # Clean up
    deleted = client.delete(test_key)
    print(f"✅ Cleaned up test key. Deleted {deleted} keys.")


if __name__ == "__main__":
    test_redis_client()
