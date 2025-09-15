"""Health check endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter
from typing import Dict, Any

from ...db.mongodb import mongo_manager

router = APIRouter()

@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint including MongoDB status."""
    mongo_ok = await mongo_manager.ping()
    status = "ok" if mongo_ok else "degraded"
    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "crypto-news-aggregator",
        "version": "1.0.0",
        "mongodb": {
            "connected": mongo_ok
        }
    }
