from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import warnings

from sqlalchemy import text
from sqlalchemy.pool import QueuePool, StaticPool

from liquent_platform.persistence.database import build_engine


def test_memory_sqlite_is_one_engine_local_database_across_threads() -> None:
    engine = build_engine("sqlite://")
    try:
        assert type(engine.pool) is StaticPool
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE facts (value TEXT NOT NULL, observed_at TEXT NOT NULL)"
            ))
            connection.execute(
                text("INSERT INTO facts VALUES ('shared',:observed_at)"),
                {"observed_at": datetime(2026, 8, 27, tzinfo=timezone.utc)},
            )

        def read() -> tuple[str, str]:
            with engine.connect() as connection:
                return tuple(connection.execute(text(
                    "SELECT value,observed_at FROM facts"
                )).one())

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            with ThreadPoolExecutor(max_workers=1) as executor:
                assert executor.submit(read).result() == (
                    "shared", "2026-08-27 00:00:00+00:00",
                )
    finally:
        engine.dispose()


def test_explicit_memory_path_uses_same_shared_contract() -> None:
    engine = build_engine("sqlite:///:memory:")
    try:
        assert type(engine.pool) is StaticPool
    finally:
        engine.dispose()


def test_file_sqlite_keeps_bounded_queue_pool(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'bounded.db'}")
    try:
        assert type(engine.pool) is QueuePool
        assert engine.pool.size() == 3
        assert engine.pool._max_overflow == 2
        assert engine.pool._timeout == 5
    finally:
        engine.dispose()


def test_postgresql_keeps_bounded_pool_and_connect_timeout(monkeypatch) -> None:
    import liquent_platform.persistence.database as database

    captured: dict[str, object] = {}
    sentinel = object()

    def capture(database_url: str, **options: object) -> object:
        captured.update(database_url=database_url, **options)
        return sentinel

    monkeypatch.setattr(database, "create_engine", capture)
    result = database.build_engine(
        "postgresql+psycopg://liquent:secret@127.0.0.1:1/liquent"
    )

    assert result is sentinel
    assert captured == {
        "database_url": (
            "postgresql+psycopg://liquent:secret@127.0.0.1:1/liquent"
        ),
        "pool_pre_ping": True,
        "logging_name": "liquent",
        "pool_size": 3,
        "max_overflow": 2,
        "pool_timeout": 5,
        "connect_args": {"connect_timeout": 3},
    }
