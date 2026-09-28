"""SQLAlchemy engine and database readiness adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import sqlite3

from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.pool import StaticPool

from liquent_platform.application.health import Readiness
from liquent_platform.persistence.migrations import expected_head


def _configure_sqlite_adapters() -> None:
    """Replace Python 3.12's deprecated implicit ISO adapters explicitly."""

    sqlite3.register_adapter(date, lambda value: value.isoformat())
    sqlite3.register_adapter(datetime, lambda value: value.isoformat(" "))


def _enable_sqlite_foreign_keys(
    dbapi_connection: sqlite3.Connection, _connection_record: object,
) -> None:
    """Enable SQLite's per-connection foreign-key enforcement."""

    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def build_engine(database_url: str) -> Engine:
    """Build the process-wide engine without opening a connection."""

    url = None
    try:
        url = make_url(database_url)
    except (ArgumentError, TypeError):
        pass
    if url is None:
        raise ValueError("invalid_database_url")
    backend = url.get_backend_name()
    if backend not in {"sqlite", "postgresql"}:
        raise ValueError("unsupported_database_backend")
    if url.drivername not in {
        "sqlite", "sqlite+pysqlite", "postgresql+psycopg",
    }:
        raise ValueError("unsupported_database_driver")
    if backend == "sqlite" and any(value is not None for value in (
        url.username, url.password, url.host, url.port,
    )):
        raise ValueError("unsupported_database_url_authority")
    if backend == "sqlite" and not set(url.query) <= {
        "timeout", "check_same_thread",
    }:
        raise ValueError("unsupported_database_url_option")
    if backend == "sqlite":
        _configure_sqlite_adapters()
    options: dict[str, object] = {
        "pool_pre_ping": True,
        "logging_name": "liquent",
    }
    if backend == "sqlite" and url.database in (None, "", ":memory:"):
        options.update(
            poolclass=StaticPool,
            connect_args={"check_same_thread": False, "timeout": 5},
        )
    else:
        options.update(pool_size=3, max_overflow=2, pool_timeout=5)
        if backend == "sqlite":
            options["connect_args"] = {"timeout": 5}
        else:
            options["connect_args"] = {"connect_timeout": 3}
    engine = create_engine(database_url, **options)
    if backend == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


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
