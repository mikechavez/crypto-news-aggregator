from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, AsyncGenerator
import json
import re
import asyncio
import logging
import logging

from ..services.price_service import price_service
from ..services.article_service import article_service
from ..services.correlation_service import correlation_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Mappings for symbols, names, and CoinGecko IDs
SYMBOL_TO_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOT": "polkadot",
    "LINK": "chainlink",
}

NAME_TO_SYMBOL_MAP = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "dogecoin": "DOGE",
    "cardano": "ADA",
    "ripple": "XRP",
    "polkadot": "DOT",
    "chainlink": "LINK",
}

# 1. Required Models
class ChatMessage(BaseModel):
    role: str
    content: str

class OpenAIChatRequest(BaseModel):
    model: str = "crypto-insight-agent"
    messages: List[ChatMessage]
    stream: Optional[bool] = False

# 2. Service-Connected & Placeholder Functions
async def get_current_prices(symbols: List[str]) -> Dict:
    """Gets current prices from the price service."""
    coin_ids = [SYMBOL_TO_ID_MAP.get(s.upper()) for s in symbols if s.upper() in SYMBOL_TO_ID_MAP]
    if not coin_ids:
        return {"prices": {}}

    price_data = await price_service.get_prices(coin_ids)

    id_to_symbol_map = {v: k for k, v in SYMBOL_TO_ID_MAP.items()}

    prices = {}
    for coin_id, data in price_data.items():
        symbol = id_to_symbol_map.get(coin_id)
        if symbol and data.get('price') is not None:
            prices[symbol] = data['price']

    return {"prices": prices}

def _get_sentiment_label(score: Optional[float]) -> str:
    if score is None:
        return "unknown"
    if score > 0.2:
        return "positive"
    if score < -0.2:
        return "negative"
    return "neutral"

async def get_market_sentiment(symbols: List[str]) -> Dict:
    """Gets market sentiment from the article service."""
    try:
        logger.info(f"Fetching market sentiment for symbols: {symbols}")
        # Fetch average sentiment scores
        sentiment_scores = await article_service.get_average_sentiment_for_symbols(symbols)

        # Convert scores to labels
        sentiment_labels = {symbol: _get_sentiment_label(score) for symbol, score in sentiment_scores.items()}

        return {"sentiment": sentiment_labels}
    except Exception as e:
        logger.error(f"Error fetching market sentiment: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Could not fetch market sentiment due to a service error.")

async def analyze_price_correlation(symbol: str) -> Dict:
    """Analyzes price correlation using the correlation service."""
    base_coin_id = SYMBOL_TO_ID_MAP.get(symbol.upper())
    if not base_coin_id:
        return {"correlation": {}}

    # Correlate against a predefined list of major coins
    target_symbols = ["BTC", "ETH", "SOL"]
    target_coin_ids = [
        SYMBOL_TO_ID_MAP.get(s) for s in target_symbols 
        if s.upper() in SYMBOL_TO_ID_MAP and s.upper() != symbol.upper()
    ]

    if not target_coin_ids:
        return {"correlation": {}}

    correlation_data = await correlation_service.calculate_correlation(base_coin_id, target_coin_ids)

    id_to_symbol_map = {v: k for k, v in SYMBOL_TO_ID_MAP.items()}
    
    # Format the response with symbols and rounded correlation values
    formatted_correlation = {
        id_to_symbol_map.get(coin_id): round(corr, 2) 
        for coin_id, corr in correlation_data.items() if corr is not None
    }

    return {"correlation": formatted_correlation}

# 3. Query Processing and Endpoint

def extract_symbols(text: str) -> List[str]:
    """Extracts crypto symbols (e.g., BTC, ETH) and names (e.g., Bitcoin) from text."""
    text = text.lower()
    found_symbols = set()

    # 1. Extract direct symbols like BTC, ETH
    # Create a regex pattern for all known symbols
    symbol_keys = "|".join(SYMBOL_TO_ID_MAP.keys())
    direct_symbols = re.findall(rf'\b({symbol_keys})\b', text, re.IGNORECASE)
    for symbol in direct_symbols:
        found_symbols.add(symbol.upper())

    # 2. Extract full names like "bitcoin" and map to symbol
    for name, symbol in NAME_TO_SYMBOL_MAP.items():
        if name in text:
            found_symbols.add(symbol)
            
    return list(found_symbols)

def classify_intent(text: str) -> str:
    """Classifies user intent from the message content."""
    text = text.lower()
    if any(keyword in text for keyword in ["correlate", "correlation", "relationship"]):
        return "correlation_analysis"
    if any(keyword in text for keyword in ["sentiment", "feel about", "opinion"]):
        return "sentiment_analysis"
    if any(keyword in text for keyword in ["price", "value", "cost", "how much"]):
        return "price_inquiry"
    return "price_inquiry"  # Default to price inquiry

async def stream_response(response_generator: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    async for chunk in response_generator:
        yield f"data: {json.dumps(chunk)}\n\n"
    yield "data: [DONE]\n\n"

async def generate_response_content(intent: str, symbols: List[str]) -> str:
    """Generates a response based on intent and symbols."""
    if not symbols:
        return "I can provide information about cryptocurrencies. Please specify a symbol like BTC or ETH."

    if intent == "price_inquiry":
        data = await get_current_prices(symbols)
        prices = data.get("prices", {})
        return ", ".join([f"The current price of {s} is ${p:,.2f}" for s, p in prices.items()])

    elif intent == "sentiment_analysis":
        try:
            data = await get_market_sentiment(symbols)
            sentiments = data.get("sentiment", {})
            return ", ".join([f"The current market sentiment for {s} is {sent}" for s, sent in sentiments.items()])
        except HTTPException as e:
            return f"An error occurred while fetching market sentiment: {e.detail}"

    elif intent == "correlation_analysis":
        if not symbols:
            return "Please specify a symbol for correlation analysis."
        data = await analyze_price_correlation(symbols[0])
        correlation = data.get("correlation", {})
        corr_str = ", ".join([f"{key} ({val})" for key, val in correlation.items()])
        return f"{symbols[0]} is correlated with: {corr_str}."

    return "I'm not sure how to help with that."

@router.post("/completions")
async def chat_completions(request: OpenAIChatRequest):
    """OpenAI-compatible chat completions endpoint."""
    logger.info("Received chat completion request")
    last_message = request.messages[-1].content
    symbols = extract_symbols(last_message)
    intent = classify_intent(last_message)

    logger.info(f"Classified intent as '{intent}' for symbols {symbols}")
    if intent == "sentiment_analysis":
        logger.info("Performing sentiment analysis query.")

    if request.stream:
        async def response_generator():
            content = await generate_response_content(intent, symbols)
            response_chunk = {
                "choices": [
                    {
                        "delta": {"role": "assistant", "content": content},
                        "finish_reason": "stop"
                    }
                ]
            }
            yield response_chunk

        async def stream_chunks():
            async for chunk in response_generator():
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_chunks(), media_type="text/event-stream")

    else:
        try:
            content = await generate_response_content(intent, symbols)
            response = {
                "choices": [
                    {
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop"
                    }
                ]
            }
            return response
        except HTTPException as e:
            logger.error(f"HTTPException in chat_completions: {e.detail}")
            return {
                "choices": [
                    {
                        "message": {"role": "assistant", "content": f"An error occurred: {e.detail}"},
                        "finish_reason": "stop"
                    }
                ]
            }

