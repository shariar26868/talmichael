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
