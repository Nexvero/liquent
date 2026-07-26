"""SQLAlchemy engine and database readiness adapter."""

from __future__ import annotations

from dataclasses import dataclass

from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from liquent_platform.application.health import Readiness
from liquent_platform.persistence.migrations import expected_head


def build_engine(database_url: str) -> Engine:
    """Build the process-wide engine without opening a connection."""

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        pool_timeout=5,
        connect_args={"connect_timeout": 3} if database_url.startswith("postgresql") else {},
        logging_name="liquent",
    )


@dataclass(frozen=True)
class DatabaseReadinessProbe:
    engine: Engine

    def check(self) -> Readiness:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                current = MigrationContext.configure(connection).get_current_revision()
        except SQLAlchemyError:
            return Readiness(ready=False, reason="database_unavailable")
        if current != expected_head():
            return Readiness(ready=False, reason="schema_revision_mismatch")
        return Readiness(ready=True, reason="database_ready")
