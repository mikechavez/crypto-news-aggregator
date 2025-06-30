from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Core settings
    DEBUG: bool = False
    PROJECT_NAME: str = "Crypto News Aggregator"
    VERSION: str = "0.1.0"

    # PostgreSQL settings (kept for backward compatibility)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "crypto_news"
    POSTGRES_URL: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"
    
    # MongoDB settings
    MONGODB_URI: str = ""  # e.g., "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/"
    MONGODB_NAME: str = "crypto_news"  # Default database name
    
    # For backward compatibility
    DATABASE_URL: str = POSTGRES_URL

    # API Keys (these will be loaded from environment variables)
    NEWS_API_KEY: str = ""  # Kept for backward compatibility
    TWITTER_BEARER_TOKEN: str = ""
    POLYMARKET_API_KEY: str = ""
    
    # Realtime NewsAPI settings
    REALTIME_NEWSAPI_URL: str = "http://localhost:3000"  # URL of the self-hosted realtime-newsapi
    REALTIME_NEWSAPI_TIMEOUT: int = 30  # Request timeout in seconds
    REALTIME_NEWSAPI_MAX_RETRIES: int = 3  # Max retries for API calls

    # Redis settings (for direct Redis protocol - optional)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Upstash Redis REST API settings
    UPSTASH_REDIS_REST_URL: str = ""  # e.g., "https://your-instance.upstash.io"
    UPSTASH_REDIS_TOKEN: str = ""     # Your Upstash REST token
    
    # Celery settings (using Redis for local development)
    CELERY_BROKER_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    CELERY_RESULT_BACKEND: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    # Email settings
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_SENDER: str = ""

    # Cache settings
    CACHE_EXPIRE: int = 3600  # 1 hour
    
    # Database sync settings
    ENABLE_DB_SYNC: bool = False  # Enable/disable database synchronization

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
