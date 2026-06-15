import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.base import Base
import src.db.models  # noqa: F401 — ensures all models are registered

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Read DB URL from environment so Docker and local dev both work without editing alembic.ini
_database_url = (
    os.getenv("ALEMBIC_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or config.get_main_option("sqlalchemy.url")
)
if _database_url and _database_url.startswith("postgresql+asyncpg://"):
    _database_url = _database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
config.set_main_option("sqlalchemy.url", _database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
