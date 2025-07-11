from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Core settings
    DEBUG: bool = False
    PROJECT_NAME: str = "Crypto News Aggregator"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

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

    # Security settings
    SECRET_KEY: str = "your-secret-key-here"  # Change this to a secure secret key
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days
    
    # CORS settings
    CORS_ORIGINS: str = "*"  # In production, replace with specific origins
    
    # Email settings
    SMTP_SERVER: str = "smtp.gmail.com"  # Default to Gmail's SMTP server
    SMTP_PORT: int = 465  # SSL port for Gmail
    SMTP_USERNAME: str = ""  # Your email username
    SMTP_PASSWORD: str = ""  # Your email password or app password
    EMAILS_FROM_EMAIL: str = "noreply@example.com"  # Sender email
    EMAILS_FROM_NAME: str = "Crypto News Aggregator"  # Sender name
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@example.com"  # Should match SMTP username for most providers
    EMAIL_FROM_NAME: str = "Crypto News Aggregator"
    EMAIL_DOMAIN: str = "cryptonewsaggregator.com"  # Used for Message-ID header
    SUPPORT_EMAIL: str = "support@cryptonewsaggregator.com"
    ALERT_EMAIL: str = "alerts@cryptonewsaggregator.com"  # Email address to send alerts to
    
    # Email tracking settings
    EMAIL_TRACKING_ENABLED: bool = True
    EMAIL_TRACKING_PIXEL_URL: str = "{BASE_URL}/api/v1/emails/track/open/{message_id}"
    EMAIL_TRACKING_CLICK_URL: str = "{BASE_URL}/api/v1/emails/track/click/{message_id}/{link_hash}"
    EMAIL_UNSUBSCRIBE_URL: str = "{BASE_URL}/api/v1/emails/unsubscribe/{token}"
    
    # Email rate limiting
    EMAIL_RATE_LIMIT: int = 100  # Max emails per hour
    EMAIL_RATE_LIMIT_WINDOW: int = 3600  # 1 hour in seconds
    
    # Email retry settings
    EMAIL_MAX_RETRIES: int = 3
    EMAIL_RETRY_DELAY: int = 60  # seconds
    
    # Price monitoring settings
    PRICE_CHECK_INTERVAL: int = 300  # 5 minutes in seconds
    PRICE_CHANGE_THRESHOLD: float = 3.0  # 3% change to trigger alert
    MIN_ALERT_INTERVAL: int = 1800  # 30 minutes in seconds
    
    # CoinGecko API settings
    COINGECKO_API_URL: str = "https://api.coingecko.com/api/v3"
    COINGECKO_API_KEY: str = ""  # Optional API key for higher rate limits
    
    # News source settings
    ENABLED_NEWS_SOURCES: list[str] = ["coindesk", "bloomberg"]
    NEWS_FETCH_INTERVAL: int = 300  # 5 minutes in seconds
    MAX_ARTICLES_PER_SOURCE: int = 20
    
    # Source-specific settings
    COINDESK_API_KEY: str = ""  # Optional API key for CoinDesk
    BLOOMBERG_RATE_LIMIT: int = 10  # Max requests per minute
    
    # Article processing
    MIN_ARTICLE_LENGTH: int = 100  # Minimum characters for an article to be processed
    MAX_ARTICLE_AGE_DAYS: int = 7  # Ignore articles older than this
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-here"  # Change this to a secure secret key
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    API_KEY: str = "test-api-key"  # For testing purposes

    # Cache settings
    CACHE_EXPIRE: int = 3600  # 1 hour
    
    # Database sync settings
    ENABLE_DB_SYNC: bool = False  # Enable/disable database synchronization

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

# Create a settings instance for direct import
settings = get_settings()
