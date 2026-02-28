from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Convert sync URL to async
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Production-ready connection pool configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,           # Base connections per worker
    max_overflow=30,        # Extra connections under load
    pool_pre_ping=True,     # Verify connections are alive
    pool_recycle=300,       # Recycle connections every 5 min
    pool_timeout=30,        # Timeout waiting for connection
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
