"""
Test script for the OpenAI-compatible chat completions endpoint.
"""

import httpx
import asyncio
import json

BASE_URL = "http://127.0.0.1:8000"
ENDPOINT = "/v1/chat/completions"


async def send_request(client: httpx.AsyncClient, payload: dict):
    """Helper function to send a request and print the response."""
    print(f"--- Sending Request ---")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        if payload.get("stream", False):
            print("--- Streaming Response ---")
            async with client.stream(
                "POST", f"{BASE_URL}{ENDPOINT}", json=payload, timeout=30
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk.strip():
                        print(chunk.decode("utf-8"))
        else:
            response = await client.post(
                f"{BASE_URL}{ENDPOINT}", json=payload, timeout=30
            )
            response.raise_for_status()
            print("--- Non-Streaming Response ---")
            print(json.dumps(response.json(), indent=2))

    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print(f"Request Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    print("------------------------\n")


async def main():
    """Main function to run all test cases."""
    async with httpx.AsyncClient() as client:
        # 1. Test Price Inquiry (Non-streaming)
        price_payload = {
            "model": "crypto-insight-agent",
            "messages": [
                {"role": "user", "content": "What is the current price of BTC and ETH?"}
            ],
            "stream": False,
        }
        await send_request(client, price_payload)

        # 2. Test Sentiment Analysis (Non-streaming)
        sentiment_payload = {
            "model": "crypto-insight-agent",
            "messages": [
                {"role": "user", "content": "What is the market sentiment for Solana?"}
            ],
            "stream": False,
        }
        await send_request(client, sentiment_payload)

        # 3. Test Correlation Analysis (Non-streaming)
        correlation_payload = {
            "model": "crypto-insight-agent",
            "messages": [
                {"role": "user", "content": "How does ETH correlate with BTC?"}
            ],
            "stream": False,
        }
        await send_request(client, correlation_payload)

        # 4. Test Streaming Response
        streaming_payload = {
            "model": "crypto-insight-agent",
            "messages": [{"role": "user", "content": "What's the price of SOL?"}],
            "stream": True,
        }
        await send_request(client, streaming_payload)


if __name__ == "__main__":
    asyncio.run(main())
