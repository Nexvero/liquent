from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import text

from liquent_platform.persistence.database import build_engine


def test_file_sqlite_timeout_is_central_despite_url_override(tmp_path) -> None:
    engine = build_engine(
        f"sqlite:///{tmp_path / 'timeout.db'}?timeout=0.001"
    )
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("PRAGMA busy_timeout")) == 5000
    finally:
        engine.dispose()


def test_memory_sqlite_timeout_and_thread_option_override_url_values() -> None:
    engine = build_engine(
        "sqlite://?timeout=0.001&check_same_thread=true"
    )
    try:
        with engine.begin() as connection:
            assert connection.scalar(text("PRAGMA busy_timeout")) == 5000
            connection.execute(text("CREATE TABLE shared (value TEXT NOT NULL)"))
            connection.execute(text("INSERT INTO shared VALUES ('central')"))

        def read() -> str:
            with engine.connect() as connection:
                return connection.scalar(text("SELECT value FROM shared"))

        with ThreadPoolExecutor(max_workers=1) as executor:
            assert executor.submit(read).result() == "central"
    finally:
        engine.dispose()


def test_file_sqlite_factory_options_are_explicit(monkeypatch, tmp_path) -> None:
    import liquent_platform.persistence.database as database

    captured: dict[str, object] = {}
    sentinel = object()

    def capture(database_url: str, **options: object) -> object:
        captured.update(database_url=database_url, **options)
        return sentinel

    monkeypatch.setattr(database, "create_engine", capture)
    monkeypatch.setattr(database.event, "listen", lambda *_args: None)
    url = f"sqlite:///{tmp_path / 'explicit.db'}?timeout=99"

    assert database.build_engine(url) is sentinel
    assert captured["connect_args"] == {"timeout": 5}
    assert captured["pool_size"] == 3
    assert captured["max_overflow"] == 2
    assert captured["pool_timeout"] == 5


def test_memory_sqlite_factory_options_are_explicit(monkeypatch) -> None:
    import liquent_platform.persistence.database as database

    captured: dict[str, object] = {}
    sentinel = object()

    def capture(database_url: str, **options: object) -> object:
        captured.update(database_url=database_url, **options)
        return sentinel

    monkeypatch.setattr(database, "create_engine", capture)
    monkeypatch.setattr(database.event, "listen", lambda *_args: None)

    assert database.build_engine(
        "sqlite://?timeout=99&check_same_thread=true"
    ) is sentinel
    assert captured["connect_args"] == {
        "check_same_thread": False,
        "timeout": 5,
    }
    assert "pool_size" not in captured
    assert "pool_timeout" not in captured


def test_postgresql_connect_options_remain_separate(monkeypatch) -> None:
    import liquent_platform.persistence.database as database

    captured: dict[str, object] = {}
    sentinel = object()

    def capture(database_url: str, **options: object) -> object:
        captured.update(database_url=database_url, **options)
        return sentinel

    monkeypatch.setattr(database, "create_engine", capture)

    assert database.build_engine(
        "postgresql+psycopg://actor:secret@127.0.0.1:1/liquent"
        "?connect_timeout=99"
    ) is sentinel
    assert captured["connect_args"] == {"connect_timeout": 3}
    assert "timeout" not in captured["connect_args"]
    assert "check_same_thread" not in captured["connect_args"]
