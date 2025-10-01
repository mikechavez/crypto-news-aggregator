#!/usr/bin/env python3
"""
Performance testing script for API endpoints.
Tests concurrent requests to Bitcoin and Ethereum endpoints.
"""
import asyncio
import time
import logging
from typing import List, Dict, Any
import aiohttp
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class APILoadTester:
    """Load testing utility for API endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "test-key"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def make_request(
        self, endpoint: str, method: str = "GET", params: Dict = None
    ) -> Dict[str, Any]:
        """Make a single API request."""
        url = f"{self.base_url}{endpoint}"
        headers = {"X-API-Key": self.api_key}

        start_time = time.time()
        try:
            async with self.session.request(
                method, url, params=params, headers=headers
            ) as response:
                duration = time.time() - start_time
                result = {
                    "success": response.status == 200,
                    "status_code": response.status,
                    "duration_ms": round(duration * 1000, 2),
                    "response_size": (
                        len(await response.read()) if response.status == 200 else 0
                    ),
                }
                return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Request failed: {e}")
            return {
                "success": False,
                "status_code": 0,
                "duration_ms": round(duration * 1000, 2),
                "error": str(e),
            }

    async def test_concurrent_requests(
        self, endpoint: str, num_requests: int = 10
    ) -> Dict[str, Any]:
        """Test concurrent requests to an endpoint."""
        logger.info(f"Testing {num_requests} concurrent requests to {endpoint}")

        start_time = time.time()

        # Create concurrent tasks
        tasks = [self.make_request(endpoint) for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # Analyze results
        successful = [
            r for r in results if isinstance(r, dict) and r.get("success", False)
        ]
        failed = [
            r for r in results if isinstance(r, dict) and not r.get("success", False)
        ]

        avg_duration = (
            sum(r["duration_ms"] for r in successful) / len(successful)
            if successful
            else 0
        )
        min_duration = min(r["duration_ms"] for r in successful) if successful else 0
        max_duration = max(r["duration_ms"] for r in successful) if successful else 0

        return {
            "endpoint": endpoint,
            "total_requests": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) * 100,
            "total_time_ms": round(total_time * 1000, 2),
            "avg_duration_ms": round(avg_duration, 2),
            "min_duration_ms": round(min_duration, 2),
            "max_duration_ms": round(max_duration, 2),
            "requests_per_second": (
                len(successful) / total_time if total_time > 0 else 0
            ),
        }

    async def test_bitcoin_endpoints(self, num_requests: int = 5) -> Dict[str, Any]:
        """Test Bitcoin-related endpoints."""
        endpoints = [
            "/api/v1/price/bitcoin/current",
            "/api/v1/price/bitcoin/history?hours=24",
            "/api/v1/price/analysis/bitcoin",
        ]

        results = {}
        for endpoint in endpoints:
            try:
                result = await self.test_concurrent_requests(endpoint, num_requests)
                results[endpoint] = result
                logger.info(
                    f"Endpoint {endpoint}: {result['success_rate']:.1f}% success rate, {result['avg_duration_ms']:.1f}ms avg"
                )
                # Small delay between endpoint tests
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to test {endpoint}: {e}")
                results[endpoint] = {"error": str(e)}

        return results

    async def test_ethereum_endpoints(self, num_requests: int = 5) -> Dict[str, Any]:
        """Test Ethereum-related endpoints."""
        endpoints = ["/api/v1/price/analysis/ethereum"]

        results = {}
        for endpoint in endpoints:
            try:
                result = await self.test_concurrent_requests(endpoint, num_requests)
                results[endpoint] = result
                logger.info(
                    f"Endpoint {endpoint}: {result['success_rate']:.1f}% success rate, {result['avg_duration_ms']:.1f}ms avg"
                )
                # Small delay between endpoint tests
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to test {endpoint}: {e}")
                results[endpoint] = {"error": str(e)}

        return results


async def main():
    """Main function to run load tests."""
    parser = argparse.ArgumentParser(description="API Load Testing Script")
    parser.add_argument(
        "--url", default="http://localhost:8000", help="Base URL of the API"
    )
    parser.add_argument(
        "--api-key", default="test-key", help="API key for authentication"
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=5,
        help="Number of concurrent requests per endpoint",
    )
    parser.add_argument(
        "--endpoints",
        choices=["bitcoin", "ethereum", "both"],
        default="both",
        help="Which endpoints to test",
    )

    args = parser.parse_args()

    async with APILoadTester(args.url, args.api_key) as tester:
        logger.info(f"Starting load tests against {args.url}")

        if args.endpoints in ["bitcoin", "both"]:
            logger.info("=== Testing Bitcoin Endpoints ===")
            bitcoin_results = await tester.test_bitcoin_endpoints(args.requests)
            for endpoint, result in bitcoin_results.items():
                if "error" not in result:
                    print(f"\n{endpoint}:")
                    print(f"  Success Rate: {result['success_rate']:.1f}%")
                    print(f"  Avg Response Time: {result['avg_duration_ms']:.1f}ms")
                    print(
                        f"  Min/Max Response Time: {result['min_duration_ms']:.1f}ms / {result['max_duration_ms']:.1f}ms"
                    )
                    print(f"  Requests/sec: {result['requests_per_second']:.1f}")

        if args.endpoints in ["ethereum", "both"]:
            logger.info("=== Testing Ethereum Endpoints ===")
            ethereum_results = await tester.test_ethereum_endpoints(args.requests)
            for endpoint, result in ethereum_results.items():
                if "error" not in result:
                    print(f"\n{endpoint}:")
                    print(f"  Success Rate: {result['success_rate']:.1f}%")
                    print(f"  Avg Response Time: {result['avg_duration_ms']:.1f}ms")
                    print(
                        f"  Min/Max Response Time: {result['min_duration_ms']:.1f}ms / {result['max_duration_ms']:.1f}ms"
                    )
                    print(f"  Requests/sec: {result['requests_per_second']:.1f}")

        logger.info("Load testing completed!")


if __name__ == "__main__":
    asyncio.run(main())
