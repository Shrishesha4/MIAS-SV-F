"""MRD query governance: concurrency semaphore, rate limiting, response cache, audit."""

import hashlib
import json
import time
import uuid
from datetime import datetime
from functools import wraps
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.redis_client import get_redis
from app.database import get_db
from app.models.mrd_audit import MrdQueryAudit
from app.models.user import User
from app.api.deps import get_current_user

# ── Redis key prefixes ───────────────────────────────────────────────
_SEMAPHORE_USER_PREFIX = "mrd:sem:user:"
_SEMAPHORE_GLOBAL_KEY = "mrd:sem:global"
_RATE_LIMIT_PREFIX = "mrd:rl:"
_CACHE_PREFIX = "mrd:cache:"
_SNAPSHOT_VERSION_KEY = "mrd:snapshot_version"

_SEMAPHORE_TTL = 120  # Auto-release after 2 min (safety net)
_CACHE_TTL = 300  # 5 min


# ── Lua scripts for atomic semaphore operations ──────────────────────

# KEYS[1] = user key, KEYS[2] = global key
# ARGV[1] = max per user, ARGV[2] = max global, ARGV[3] = token, ARGV[4] = TTL
_ACQUIRE_LUA = """
local user_count = redis.call('SCARD', KEYS[1])
if user_count >= tonumber(ARGV[1]) then return 0 end
local global_count = redis.call('SCARD', KEYS[2])
if global_count >= tonumber(ARGV[2]) then return 0 end
redis.call('SADD', KEYS[1], ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[4])
redis.call('SADD', KEYS[2], ARGV[3])
redis.call('EXPIRE', KEYS[2], ARGV[4])
return 1
"""

# KEYS[1] = user key, KEYS[2] = global key, ARGV[1] = token
_RELEASE_LUA = """
redis.call('SREM', KEYS[1], ARGV[1])
redis.call('SREM', KEYS[2], ARGV[1])
return 1
"""


async def _acquire_semaphore(redis, user_id: str) -> str | None:
    """Acquire concurrency slot. Returns token on success, None if exhausted."""
    token = str(uuid.uuid4())
    user_key = f"{_SEMAPHORE_USER_PREFIX}{user_id}"
    result = await redis.eval(
        _ACQUIRE_LUA,
        2,
        user_key,
        _SEMAPHORE_GLOBAL_KEY,
        str(settings.MRD_MAX_CONCURRENT_PER_USER),
        str(settings.MRD_MAX_CONCURRENT_GLOBAL),
        token,
        str(_SEMAPHORE_TTL),
    )
    return token if result == 1 else None


async def _release_semaphore(redis, user_id: str, token: str) -> None:
    user_key = f"{_SEMAPHORE_USER_PREFIX}{user_id}"
    await redis.eval(
        _RELEASE_LUA,
        2,
        user_key,
        _SEMAPHORE_GLOBAL_KEY,
        token,
    )


async def check_mrd_rate_limit(user_id: str) -> None:
    """Sliding-window rate limit for MRD users. Raises 429 if exceeded."""
    redis = await get_redis()
    key = f"{_RATE_LIMIT_PREFIX}{user_id}"
    current = await redis.get(key)
    if current and int(current) >= settings.MRD_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="MRD rate limit exceeded. Try again shortly.",
        )
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, 60)
    await pipe.execute()


def _cache_key(route: str, user_id: str, filters: dict, snapshot_version: str) -> str:
    """Build deterministic cache key including snapshot version."""
    filter_hash = hashlib.sha256(
        json.dumps(filters, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return f"{_CACHE_PREFIX}{route}:{user_id}:{snapshot_version}:{filter_hash}"


async def get_cached_response(
    route: str, user_id: str, filters: dict
) -> Any | None:
    """Return cached response if available."""
    redis = await get_redis()
    snapshot_version = await redis.get(_SNAPSHOT_VERSION_KEY) or "0"
    key = _cache_key(route, user_id, filters, snapshot_version)
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    return None


async def set_cached_response(
    route: str, user_id: str, filters: dict, data: Any
) -> None:
    """Cache a response with TTL."""
    redis = await get_redis()
    snapshot_version = await redis.get(_SNAPSHOT_VERSION_KEY) or "0"
    key = _cache_key(route, user_id, filters, snapshot_version)
    await redis.set(key, json.dumps(data, default=str), ex=_CACHE_TTL)


async def write_audit(
    db: AsyncSession,
    user_id: str,
    route: str,
    filters: dict,
    rows_returned: int,
    duration_ms: int,
    audit_status: str = "ok",
) -> None:
    """Write audit row to OLTP database."""
    audit = MrdQueryAudit(
        id=str(uuid.uuid4()),
        user_id=user_id,
        route=route,
        filter_json=json.dumps(filters, default=str),
        rows_returned=rows_returned,
        duration_ms=duration_ms,
        status=audit_status,
        created_at=datetime.utcnow(),
    )
    db.add(audit)
    await db.commit()


class MrdGovernance:
    """FastAPI dependency that enforces rate limit + concurrency for an MRD request."""

    def __init__(self):
        self.token: str | None = None
        self.user_id: str | None = None
        self.redis = None

    async def __call__(self, user: User = Depends(get_current_user)) -> "MrdGovernance":
        self.user_id = user.id
        self.redis = await get_redis()

        # Rate limit
        await check_mrd_rate_limit(user.id)

        # Concurrency semaphore
        self.token = await _acquire_semaphore(self.redis, user.id)
        if not self.token:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many concurrent MRD queries. Please wait.",
            )
        return self

    async def release(self) -> None:
        if self.token and self.user_id and self.redis:
            await _release_semaphore(self.redis, self.user_id, self.token)
            self.token = None
