import os
import sys
import logging
import json
from pathlib import Path
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("redis_test")

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info("Loaded environment variables from .env file")
else:
    logger.warning("No .env file found. Using system environment variables.")

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, os.path.join(project_root, "src"))

# Import after path setup
from crypto_news_aggregator.core.redis_rest_client import RedisRESTClient
from crypto_news_aggregator.core.config import get_settings


def print_env_vars():
    """Print relevant environment variables for debugging."""
    settings = get_settings()
    logger.info("Current configuration:")
    logger.info(
        f"UPSTASH_REDIS_REST_URL: {'Set' if settings.UPSTASH_REDIS_REST_URL else 'Not set'}"
    )
    logger.info(
        f"UPSTASH_REDIS_TOKEN: {'Set' if settings.UPSTASH_REDIS_TOKEN else 'Not set'}"
    )

    # Mask the token for security
    if settings.UPSTASH_REDIS_TOKEN:
        masked_token = (
            f"{settings.UPSTASH_REDIS_TOKEN[:10]}...{settings.UPSTASH_REDIS_TOKEN[-4:]}"
        )
        logger.info(f"UPSTASH_REDIS_TOKEN (masked): {masked_token}")


def test_redis_integration():
    """Test the Redis client with the actual Upstash Redis instance."""
    logger.info("=== Starting Redis Integration Test ===")
    print_env_vars()

    # Verify environment variables
    settings = get_settings()
    if not settings.UPSTASH_REDIS_REST_URL or not settings.UPSTASH_REDIS_TOKEN:
        logger.error("Error: UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_TOKEN is not set")
        return False

    # Create a client instance
    try:
        logger.info("Creating Redis REST client...")
        client = RedisRESTClient()
        logger.info(f"Client created with base URL: {client.base_url}")
    except Exception as e:
        logger.error(f"Failed to create Redis client: {str(e)}")
        logger.error("Please check your UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_TOKEN")
        return False

    # Test ping
    logger.info("Testing ping...")
    try:
        ping_result = client.ping()
        if ping_result:
            logger.info("✅ Ping successful")
        else:
            logger.error("❌ Ping failed - No response from server")
            return False
    except Exception as e:
        logger.error(f"❌ Ping failed with error: {str(e)}")
        logger.error("This could be due to:")
        logger.error("1. Incorrect UPSTASH_REDIS_REST_URL")
        logger.error("2. Invalid or expired UPSTASH_REDIS_TOKEN")
        logger.error("3. Network connectivity issues to Upstash")
        return False

    # Test set/get operations
    test_key = "test:integration"
    test_value = "test_value_123"

    try:
        # Test SET
        logger.info(f"Testing SET: {test_key} = {test_value}")
        if client.set(test_key, test_value):
            logger.info("✅ Set operation successful")
        else:
            logger.error("❌ Set operation failed - No response from server")
            return False

        # Test GET
        logger.info(f"Testing GET: {test_key}")
        retrieved = client.get(test_key)
        if retrieved == test_value:
            logger.info(f"✅ Get operation successful. Retrieved: {retrieved}")
        else:
            logger.error(
                f"❌ Get operation failed. Expected '{test_value}', got '{retrieved}'"
            )
            return False

        # Test DELETE
        logger.info(f"Testing DELETE: {test_key}")
        deleted = client.delete(test_key)
        if deleted == 1:
            logger.info(f"✅ Delete successful. Deleted {deleted} key.")
        else:
            logger.warning(
                f"⚠️  Delete operation may have failed. Expected to delete 1 key, got {deleted}"
            )

        # Verify deletion
        logger.info("Verifying deletion...")
        should_be_none = client.get(test_key)
        if should_be_none is None:
            logger.info("✅ Verification successful: Key was deleted")
        else:
            logger.error(
                f"❌ Verification failed: Key still exists with value: {should_be_none}"
            )
            return False

        logger.info("=== All tests completed successfully ===")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("Starting Redis integration test...")
    success = test_redis_integration()
    if success:
        logger.info("✅ All tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed. See logs above for details.")
        sys.exit(1)
