from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine, pool


config = context.config
target_metadata = None


def database_url() -> str:
    value = config.attributes.get("database_url")
    if not isinstance(value, str) or not value:
        raise RuntimeError("database URL must be injected by the migration entry point")
    return value


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
