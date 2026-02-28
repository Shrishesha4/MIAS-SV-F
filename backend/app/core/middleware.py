"""Minimal middleware: CORS is handled by FastAPI built-in, rate-limiting via slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

# Use Redis for distributed rate limiting across multiple workers/instances
# Falls back to memory storage if Redis is unavailable
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)
