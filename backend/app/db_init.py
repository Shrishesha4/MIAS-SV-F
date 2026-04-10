from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import engine


ALEMBIC_LOCK_ID = 8042026
BACKEND_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_INI_PATH = BACKEND_ROOT / 'alembic.ini'


def _upgrade_database(connection: Connection) -> None:
    config = Config(str(ALEMBIC_INI_PATH))
    config.attributes['connection'] = connection
    command.upgrade(config, 'head')


async def run_startup_migrations() -> None:
    async with engine.connect() as connection:
        await connection.execute(text('SELECT pg_advisory_lock(:lock_id)'), {'lock_id': ALEMBIC_LOCK_ID})
        try:
            await connection.run_sync(_upgrade_database)
        finally:
            await connection.execute(text('SELECT pg_advisory_unlock(:lock_id)'), {'lock_id': ALEMBIC_LOCK_ID})
