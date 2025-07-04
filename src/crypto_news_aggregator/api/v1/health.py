"""Health check endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from typing import Dict, Any

router = APIRouter()

@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "crypto-news-aggregator",
        "version": "1.0.0"
    }
