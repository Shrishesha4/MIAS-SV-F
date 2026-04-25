from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.engine import Connection

from app.core.security import get_password_hash
from app.database import AsyncSessionLocal, engine
from app.services.charge_sync import sync_charge_price_categories
from app.models.user import User, UserRole


ALEMBIC_LOCK_ID = 8042026
BACKEND_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_INI_PATH = BACKEND_ROOT / 'alembic.ini'
DEFAULT_ADMIN_USERNAME = 'a'
DEFAULT_ADMIN_EMAIL = 'a@saveetha.com'
DEFAULT_ADMIN_PASSWORD = 'a'


def _upgrade_database(connection: Connection) -> None:
    config = Config(str(ALEMBIC_INI_PATH))
    config.attributes['connection'] = connection
    command.upgrade(config, 'head')


async def ensure_default_admin_user() -> None:
    async with AsyncSessionLocal() as session:
        existing_admin = (
            await session.execute(select(User).where(User.role == UserRole.ADMIN).limit(1))
        ).scalar_one_or_none()

        if existing_admin:
            return

        default_user = (
            await session.execute(
                select(User).where(User.username == DEFAULT_ADMIN_USERNAME).limit(1)
            )
        ).scalar_one_or_none()

        if default_user:
            default_user.email = DEFAULT_ADMIN_EMAIL
            default_user.password_hash = get_password_hash(DEFAULT_ADMIN_PASSWORD)
            default_user.role = UserRole.ADMIN
            default_user.is_active = True
        else:
            session.add(User(
                id=str(uuid4()),
                username=DEFAULT_ADMIN_USERNAME,
                email=DEFAULT_ADMIN_EMAIL,
                password_hash=get_password_hash(DEFAULT_ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            ))

        await session.commit()


async def repair_charge_tiers() -> None:
    async with AsyncSessionLocal() as session:
        await sync_charge_price_categories(session)
        await session.commit()


async def run_startup_migrations() -> None:
    async with engine.connect() as connection:
        await connection.execute(text('SELECT pg_advisory_lock(:lock_id)'), {'lock_id': ALEMBIC_LOCK_ID})
        try:
            await connection.run_sync(_upgrade_database)
            # The advisory lock is session-scoped, but the SELECT above still
            # opens an implicit transaction on this connection. Commit here so
            # Alembic version updates and schema DDL are persisted before any
            # other worker is allowed to proceed.
            await connection.commit()
            # Run post-migration bootstrap while still holding the same advisory
            # lock, but after Alembic has committed its own transaction.
            await ensure_default_admin_user()
            await repair_charge_tiers()
        except Exception:
            await connection.rollback()
            raise
        finally:
            await connection.execute(text('SELECT pg_advisory_unlock(:lock_id)'), {'lock_id': ALEMBIC_LOCK_ID})
