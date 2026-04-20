from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://mias:mias_secret@localhost:5434/mias_mp"

    # Analytics / snapshot database (MRD read-only queries)
    ANALYTICS_DATABASE_URL: str | None = None

    # Redis (for rate limiting and caching)
    REDIS_URL: str = "redis://localhost:6381"

    # JWT
    JWT_SECRET_KEY: str = "mias-super-secret-jwt-key-change-in-production-256bit"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://100.81.224.31:5173", "http://100.81.224.31:4173"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 200
    MRD_RATE_LIMIT_PER_MINUTE: int = 60
    MRD_MAX_CONCURRENT_PER_USER: int = 3
    MRD_MAX_CONCURRENT_GLOBAL: int = 50

    # App
    DEBUG: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
