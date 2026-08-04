# app/core/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Israel News & Political Intelligence API"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "talmicahel"

    # Auth
    secret_key: str = "talmicahel_jwt_secret_key_32chars_min"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # AI Keys (all optional — features degrade gracefully)
    openai_api_key: str = ""
    perplexity_api_key: str = ""
    gemini_api_key: str = ""
    claude_api_key: str = ""
    youtube_api_key: str = ""  # Optional — YouTube Data API v3 key

    # Licensed news API keys
    newsapi_key: str = ""
    newsdata_io_key: str = ""
    worldnews_api_key: str = ""
    currents_api_key: str = ""
    mediastack_api_key: str = ""

    # Image enrichment
    unsplash_access_key: str = ""  # Free key from unsplash.com/oauth/applications

    # Celery / Broker
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    # External fact-check APIs
    google_factcheck_api_key: str = ""
    # Redis (optional — used for multi-instance caching)
    redis_url: str = ""

    # Scheduler settings
    scheduler_enabled: bool = True
    scheduler_timezone: str = "Asia/Jerusalem"

    class Config:
        env_file = ".env"


settings = Settings()
