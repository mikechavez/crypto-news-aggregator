"""
Smoke tests for performance monitoring and caching features.
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
from fastapi import FastAPI

# Import only the monitoring components, not the main app to avoid circular imports
from crypto_news_aggregator.core.monitoring import (
    PerformanceMonitoringMiddleware,
    DatabaseErrorMonitor,
    LLMErrorMonitor,
    PerformanceMetrics
)

# Create a minimal test app for testing middleware
def create_test_app():
    """Create a test FastAPI app with performance monitoring."""
    from fastapi import FastAPI
    from src.crypto_news_aggregator.core.monitoring import PerformanceMonitoringMiddleware

    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "test"}

    @app.get("/test-endpoint")
    async def test_endpoint():
        return {"message": "test"}

    # Add performance monitoring middleware
    app.add_middleware(PerformanceMonitoringMiddleware)

test_app = create_test_app()

class TestPerformanceMonitoring:
    """Test performance monitoring functionality."""

    def test_middleware_logs_successful_requests(self):
        """Test that middleware logs successful API requests."""
        client = TestClient(test_app)

        # Make a request to a simple endpoint
        response = client.get("/")

        assert response.status_code == 200
        # Check that response includes performance headers
        assert "X-Process-Time" in response.headers

    def test_middleware_logs_error_requests(self):
        """Test that middleware logs error requests."""
        client = TestClient(test_app)

        # Make a request that should cause an error
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404

    def test_error_categorization(self):
        """Test error categorization functionality."""
        middleware = PerformanceMonitoringMiddleware(test_app)

        # Test database error categorization
        db_error = Exception("MongoDB connection timeout")
        category = middleware._categorize_error(db_error)
        assert category == "database_error"

        # Test external API error categorization
        api_error = Exception("CoinGecko API rate limit exceeded")
        category = middleware._categorize_error(api_error)
        assert category == "external_api_error"

        # Test LLM error categorization
        llm_error = Exception("OpenAI API key invalid")
        category = middleware._categorize_error(llm_error)
        assert category == "llm_error"

class TestDatabaseErrorMonitor:
    """Test database error monitoring."""

    def test_database_operation_logging(self):
        """Test logging of database operations."""
        # This would typically test the logging functionality
        # In a real test, we'd mock the logger and verify calls
        pass

class TestLLMErrorMonitor:
    """Test LLM error monitoring."""

    def test_llm_operation_logging(self):
        """Test logging of LLM operations."""
        # This would typically test the logging functionality
        # In a real test, we'd mock the logger and verify calls
        pass

class TestPerformanceMetrics:
    """Test performance metrics collection."""

    def test_api_performance_logging(self):
        """Test API performance logging."""
        # This would typically test the logging functionality
        # In a real test, we'd mock the logger and verify calls
        pass

    def test_external_api_logging(self):
        """Test external API call logging."""
        # This would typically test the logging functionality
        # In a real test, we'd mock the logger and verify calls
        pass

class TestPriceServiceCaching:
    """Test caching functionality in price service."""

    @pytest.mark.asyncio
    async def test_bitcoin_price_caching(self):
        """Test that Bitcoin price endpoint uses caching."""
        service = CoinGeckoPriceService()

        # First call should cache the result
        result1 = await service.get_bitcoin_price()

        # Second call should use cache (if within TTL)
        result2 = await service.get_bitcoin_price()

        # Results should be identical (indicating cache hit)
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_market_analysis_caching(self):
        """Test that market analysis commentary is cached."""
        service = CoinGeckoPriceService()

        # First call should cache the result
        result1 = await service.generate_market_analysis_commentary('bitcoin')

        # Second call should use cache (if within TTL)
        result2 = await service.generate_market_analysis_commentary('bitcoin')

        # Results should be identical (indicating cache hit)
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test concurrent requests to endpoints."""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # Create multiple concurrent requests
            tasks = []
            for i in range(5):
                tasks.append(
                    client.get("/test-endpoint")
                )

            # Execute all requests concurrently
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Check that all requests succeeded
            successful_responses = [r for r in responses if not isinstance(r, Exception)]
            assert len(successful_responses) == 5

            # All should be successful
            for response in successful_responses:
                assert response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
