import json
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import decode_token
from app.core.redis_client import get_redis
from app.models.user import User, UserRole

security = HTTPBearer()

_USER_CACHE_TTL = 300  # 5 minutes


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")

    # Try Redis cache first
    redis = await get_redis()
    cache_key = f"user:{user_id}"
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        if not data.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        # Reconstruct a lightweight User-like object from cache
        user = User(
            id=data["id"],
            username=data["username"],
            role=UserRole(data["role"]),
            is_active=data["is_active"],
            email=data.get("email"),
        )
        return user

    # Cache miss — hit DB
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Populate cache
    await redis.set(
        cache_key,
        json.dumps({
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "is_active": user.is_active,
            "email": user.email,
        }),
        ex=_USER_CACHE_TTL,
    )

    return user


async def invalidate_user_cache(user_id: str) -> None:
    """Call after any mutation to a User row (block/unblock/role change)."""
    redis = await get_redis()
    await redis.delete(f"user:{user_id}")


def require_role(*roles: UserRole):
    async def role_checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        allowed_roles = {role.value for role in roles}
        current_role = user.role.value if isinstance(user.role, UserRole) else str(user.role)

        if current_role not in allowed_roles:
            # Cached role can be stale after role updates; re-check DB once before denying.
            result = await db.execute(select(User).where(User.id == user.id))
            fresh_user = result.scalar_one_or_none()

            if fresh_user and fresh_user.is_active:
                fresh_role = (
                    fresh_user.role.value
                    if isinstance(fresh_user.role, UserRole)
                    else str(fresh_user.role)
                )
                if fresh_role in allowed_roles:
                    await invalidate_user_cache(user.id)
                    return fresh_user

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker
