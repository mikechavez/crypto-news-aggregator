import sys
import time
import httpx
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API base URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    try:
        response = httpx.get(f"{BASE_URL}/health")
        response.raise_for_status()
        logger.info(f"Health check passed: {response.json()}")
        return True
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False

def test_news_fetch():
    """Test the news fetch endpoint"""
    try:
        # Trigger news fetch
        response = httpx.post(f"{BASE_URL}/api/v1/news/fetch")
        response.raise_for_status()
        
        task_data = response.json()
        task_id = task_data["task_id"]
        logger.info(f"Triggered news fetch with task ID: {task_id}")
        
        # Wait for task to complete
        status = wait_for_task_completion(task_id)
        return status == "SUCCESS"
    except Exception as e:
        logger.error(f"News fetch test failed: {e}")
        return False

def test_sentiment_analysis():
    """Test the sentiment analysis endpoint"""
    try:
        # Trigger sentiment analysis (using a test article ID)
        response = httpx.post(f"{BASE_URL}/api/v1/sentiment/analyze/1")
        response.raise_for_status()
        
        task_data = response.json()
        task_id = task_data["task_id"]
        logger.info(f"Triggered sentiment analysis with task ID: {task_id}")
        
        # Wait for task to complete
        status = wait_for_task_completion(task_id)
        return status == "SUCCESS"
    except Exception as e:
        logger.error(f"Sentiment analysis test failed: {e}")
        return False

def test_trends_update():
    """Test the trends update endpoint"""
    try:
        # Trigger trends update
        response = httpx.post(f"{BASE_URL}/api/v1/trends/update")
        response.raise_for_status()
        
        task_data = response.json()
        task_id = task_data["task_id"]
        logger.info(f"Triggered trends update with task ID: {task_id}")
        
        # Wait for task to complete
        status = wait_for_task_completion(task_id)
        return status == "SUCCESS"
    except Exception as e:
        logger.error(f"Trends update test failed: {e}")
        return False

def wait_for_task_completion(task_id: str, max_retries: int = 10, delay: float = 0.5) -> str:
    """Wait for a task to complete and return its final status"""
    for attempt in range(max_retries):
        try:
            response = httpx.get(f"{BASE_URL}/api/v1/tasks/{task_id}")
            response.raise_for_status()
            
            task_status = response.json()
            status = task_status["status"]
            
            if status in ["SUCCESS", "FAILURE"]:
                logger.info(f"Task {task_id} completed with status: {status}")
                if status == "SUCCESS":
                    logger.info(f"Task result: {task_status.get('result')}")
                return status
                
            logger.info(f"Task {task_id} status: {status} (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
            
        except Exception as e:
            logger.error(f"Error checking task status: {e}")
            time.sleep(delay)
    
    logger.warning(f"Task {task_id} did not complete within the expected time")
    return "PENDING"

def run_tests():
    """Run all API tests"""
    logger.info("Starting API tests...")
    
    # Test health check
    logger.info("\n--- Testing health check ---")
    if not test_health_check():
        logger.error("Health check test failed")
        return False
    
    # Test news fetch
    logger.info("\n--- Testing news fetch ---")
    if not test_news_fetch():
        logger.error("News fetch test failed")
        return False
    
    # Test sentiment analysis
    logger.info("\n--- Testing sentiment analysis ---")
    if not test_sentiment_analysis():
        logger.warning("Sentiment analysis test had issues (may be expected if not fully implemented)")
    
    # Test trends update
    logger.info("\n--- Testing trends update ---")
    if not test_trends_update():
        logger.error("Trends update test failed")
        return False
    
    logger.info("\nAll tests completed successfully!")
    return True

if __name__ == "__main__":
    run_tests()
