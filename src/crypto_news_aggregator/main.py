"""Main FastAPI application module."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1 import router as api_router

app = FastAPI(
    title="Crypto News Aggregator API",
    description="API for aggregating and analyzing cryptocurrency news",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router)

# Health check endpoint is now in api/v1/health.py

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("crypto_news_aggregator.main:app", host="0.0.0.0", port=8000, reload=True)
