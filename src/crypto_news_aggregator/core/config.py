from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Core settings
    DEBUG: bool = False
    PROJECT_NAME: str = "Crypto News Aggregator"
    VERSION: str = "0.1.0"

    # Database settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "crypto_news"
    DATABASE_URL: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}/{POSTGRES_DB}"

    # API Keys (these will be loaded from environment variables)
    NEWS_API_KEY: str = ""
    TWITTER_BEARER_TOKEN: str = ""
    POLYMARKET_API_KEY: str = ""

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Celery settings
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

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
