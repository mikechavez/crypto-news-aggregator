"""
Price API endpoints for cryptocurrency price data.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ....services.price_service import price_service
from ....core.security import get_current_user
from ....models.user import UserInDB

router = APIRouter()

@router.get("/bitcoin/current")
async def get_current_bitcoin_price(
    current_user: UserInDB = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get the current Bitcoin price in USD."""
    price = await price_service.get_bitcoin_price()
    if price is None:
        raise HTTPException(
            status_code=503,
            detail="Unable to fetch Bitcoin price at this time"
        )
    return {
        "symbol": "BTC",
        "price_usd": price,
        "last_updated": datetime.utcnow().isoformat()
    }

@router.get("/bitcoin/history")
async def get_bitcoin_price_history(
    hours: int = 24,
    current_user: UserInDB = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get Bitcoin price history for the specified time window."""
    if hours < 1 or hours > 168:  # Limit to 1 hour to 1 week
        raise HTTPException(
            status_code=400,
            detail="Hours must be between 1 and 168"
        )
    
    history = price_service.get_recent_price_history(hours=hours)
    return {
        "symbol": "BTC",
        "prices": [
            {
                "price": entry["price"],
                "timestamp": entry["timestamp"].isoformat()
            }
            for entry in history
        ],
        "timeframe_hours": hours
    }

@router.get("/bitcoin/check-movement")
async def check_bitcoin_price_movement(
    current_user: UserInDB = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check for significant Bitcoin price movements.
    Returns movement details if significant movement is detected.
    """
    movement = await price_service.check_price_movement()
    if movement:
        return {
            "alert": True,
            "message": f"Significant price movement detected: {movement['change_pct']}%",
            **movement
        }
    return {"alert": False, "message": "No significant price movement detected"}
