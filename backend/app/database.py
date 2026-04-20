from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Convert sync URL to async
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Session-mode PgBouncer: each SQLAlchemy pool connection maps to one persistent
# server connection. Prepared statements, advisory locks, and SET work correctly.
# Pool sizing: workers × (pool_size + max_overflow) must stay under pgbouncer
# default_pool_size (150). Auto-worker count = (2×CPU)+1; set WEB_CONCURRENCY to override.
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=3,            # Real DB connections per worker (session mode: permanent mapping)
    max_overflow=7,         # Burst headroom; workers×(3+7)=70 max, well under pgbouncer's 150
    pool_pre_ping=True,     # Drop stale connections immediately
    pool_recycle=1800,      # Recycle every 30 min (PgBouncer server_lifetime=3600)
    pool_timeout=15,        # Fail fast — PgBouncer queue handles waiting
    # PgBouncer transaction mode doesn't support prepared statements;
    # disable asyncpg statement cache entirely.
    # pgbouncer session mode: each asyncpg connection maps permanently to one server
    # connection, so prepared statements work normally. No special connect_args needed.
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Analytics / Snapshot DB (MRD read-only) ──────────────────────────
# Separate engine for MRD queries. Never shares pool with OLTP.
# Set ANALYTICS_DATABASE_URL in env to enable. Lazily initialized.

_analytics_engine = None
_AnalyticsSessionLocal = None


def _get_analytics_engine():
    global _analytics_engine, _AnalyticsSessionLocal
    if _analytics_engine is not None:
        return _analytics_engine

    if not settings.ANALYTICS_DATABASE_URL:
        raise RuntimeError(
            "ANALYTICS_DATABASE_URL is not configured. "
            "MRD routes require a separate analytics database."
        )

    analytics_url = settings.ANALYTICS_DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://"
    )

    _analytics_engine = create_async_engine(
        analytics_url,
        echo=settings.DEBUG,
        pool_size=2,
        max_overflow=4,
        pool_recycle=1800,
        pool_pre_ping=True,
        pool_timeout=15,
    )

    _AnalyticsSessionLocal = async_sessionmaker(
        _analytics_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return _analytics_engine


def _get_analytics_session_maker():
    _get_analytics_engine()
    return _AnalyticsSessionLocal


async def get_analytics_db():
    """Yield a read-only session bound to the analytics/snapshot database."""
    session_maker = _get_analytics_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def dispose_analytics_engine():
    """Dispose the analytics engine on shutdown. Safe to call if not initialized."""
    global _analytics_engine, _AnalyticsSessionLocal
    if _analytics_engine is not None:
        await _analytics_engine.dispose()
        _analytics_engine = None
        _AnalyticsSessionLocal = None
