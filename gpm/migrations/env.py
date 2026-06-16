import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Pull GPM-specific sync URL from env (psycopg2 driver for Alembic)
gpm_alembic_url = os.environ.get(
    "GPM_ALEMBIC_DATABASE_URL",
    "postgresql+psycopg2://giraffe:giraffe@localhost:5432/apparel_textile",
)
config.set_main_option("sqlalchemy.url", gpm_alembic_url)

from gpm.models import GPMBase  # noqa: E402  — import after sys.path is set
target_metadata = GPMBase.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="gpm",
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
            include_schemas=True,
            version_table_schema="gpm",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
