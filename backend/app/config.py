from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://mias:mias_secret@localhost:5432/mias_mp"

    # Redis (for rate limiting and caching)
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET_KEY: str = "mias-super-secret-jwt-key-change-in-production-256bit"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 200

    # App
    DEBUG: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
