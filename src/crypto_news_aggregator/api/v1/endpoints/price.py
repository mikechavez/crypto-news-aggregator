"""
Price API endpoints for cryptocurrency price data.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ....services.price_service import CoinGeckoPriceService, get_price_service
from ....core.security import get_current_user
from ....models.user import UserInDB
from ....core.auth import get_api_key

router = APIRouter()


@router.get("/bitcoin/current")
async def get_current_bitcoin_price(
    price_service: CoinGeckoPriceService = Depends(get_price_service),
    api_key: str = Depends(get_api_key),
) -> Dict[str, Any]:
    """Get the current Bitcoin price in USD."""
    price = await price_service.get_bitcoin_price()
    if price is None:
        raise HTTPException(
            status_code=503, detail="Unable to fetch Bitcoin price at this time"
        )
    return {
        "symbol": "BTC",
        "price_usd": price,
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.get("/bitcoin/history")
async def get_bitcoin_price_history(
    hours: int = 24,
    price_service: CoinGeckoPriceService = Depends(get_price_service),
    api_key: str = Depends(get_api_key),
) -> Dict[str, Any]:
    """Get Bitcoin price history for the specified time window."""
    if hours < 1 or hours > 168:  # Limit to 1 hour to 1 week
        raise HTTPException(status_code=400, detail="Hours must be between 1 and 168")

    history = price_service.get_recent_price_history(hours=hours)
    return {
        "symbol": "BTC",
        "prices": [
            {"price": entry["price"], "timestamp": entry["timestamp"].isoformat()}
            for entry in history
        ],
        "timeframe_hours": hours,
    }


@router.get("/bitcoin/check-movement")
async def check_bitcoin_price_movement(
    price_service: CoinGeckoPriceService = Depends(get_price_service),
    api_key: str = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Check for significant Bitcoin price movements.
    Returns movement details if significant movement is detected.
    """
    # For now, return a simple response since check_price_movement is not implemented
    return {"alert": False, "message": "Price movement checking not implemented yet"}


@router.get("/analysis/{coin_id}")
async def get_market_analysis(
    coin_id: str,
    price_service: CoinGeckoPriceService = Depends(get_price_service),
    api_key: str = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Generate enriched market analysis commentary for a cryptocurrency.
    Includes price data, sentiment analysis, and related news.
    """
    try:
        commentary = await price_service.generate_market_analysis_commentary(coin_id)
        return {
            "coin_id": coin_id,
            "analysis": commentary,
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Unable to generate market analysis: {str(e)}"
        )
