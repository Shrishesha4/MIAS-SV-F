from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Convert sync URL to async
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Production pool — PgBouncer (transaction mode) sits in front.
# 41 workers × (5 pool + 15 overflow) = 820 max app-side conns.
# PgBouncer holds 150 real DB connections and multiplexes the rest.
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,            # Base per worker; kept small — PgBouncer buffers spikes
    max_overflow=15,        # Spike headroom per worker
    pool_pre_ping=True,     # Drop stale connections immediately
    pool_recycle=1800,      # Recycle every 30 min (PgBouncer server_lifetime=3600)
    pool_timeout=15,        # Fail fast — PgBouncer queue handles waiting
    # PgBouncer transaction mode doesn't support prepared statements;
    # disable asyncpg statement cache entirely.
    connect_args={"statement_cache_size": 0},
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
