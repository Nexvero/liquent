import sqlite3

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from liquent_platform.persistence.database import build_engine


def _assert_foreign_keys_enforced(engine) -> None:
    with engine.begin() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
        connection.execute(text("CREATE TABLE parents (id INTEGER PRIMARY KEY)"))
        connection.execute(text(
            "CREATE TABLE children ("
            "id INTEGER PRIMARY KEY,parent_id INTEGER NOT NULL,"
            "FOREIGN KEY(parent_id) REFERENCES parents(id))"
        ))
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO children VALUES (1,99)"))


@pytest.mark.parametrize("database_url", ["sqlite://", "sqlite:///:memory:"])
def test_shared_memory_sqlite_enforces_foreign_keys(database_url: str) -> None:
    engine = build_engine(database_url)
    try:
        _assert_foreign_keys_enforced(engine)
    finally:
        engine.dispose()


def test_file_sqlite_enforces_foreign_keys_on_every_new_connection(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'foreign-keys.db'}")
    try:
        with engine.connect() as first:
            assert first.scalar(text("PRAGMA foreign_keys")) == 1
        engine.dispose()
        with engine.connect() as replacement:
            assert replacement.scalar(text("PRAGMA foreign_keys")) == 1
    finally:
        engine.dispose()


def test_postgresql_does_not_install_sqlite_connect_listener(monkeypatch) -> None:
    import liquent_platform.persistence.database as database

    sentinel = object()
    listens: list[tuple[object, str, object]] = []
    monkeypatch.setattr(database, "create_engine", lambda *_args, **_kwargs: sentinel)
    monkeypatch.setattr(
        database.event, "listen",
        lambda *args: listens.append(args),
    )

    assert database.build_engine(
        "postgresql+psycopg://liquent:secret@127.0.0.1:1/liquent"
    ) is sentinel
    assert listens == []


def test_listener_closes_cursor_when_pragma_fails() -> None:
    import liquent_platform.persistence.database as database

    class Cursor:
        closed = False

        def execute(self, _statement: str) -> None:
            raise sqlite3.OperationalError("closed contract")

        def close(self) -> None:
            self.closed = True

    cursor = Cursor()

    class Connection:
        def cursor(self) -> Cursor:
            return cursor

    with pytest.raises(sqlite3.OperationalError):
        database._enable_sqlite_foreign_keys(Connection(), object())
    assert cursor.closed is True
