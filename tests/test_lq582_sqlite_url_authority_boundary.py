import pytest
from sqlalchemy import text

from liquent_platform.persistence.database import build_engine


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite://actor:do-not-disclose@host/database.db",
        "sqlite://actor@host/database.db",
        "sqlite://:do-not-disclose@/database.db",
        "sqlite://host/database.db",
        "sqlite://host:1234/database.db",
    ],
)
def test_sqlite_authority_is_rejected_before_side_effects(
    database_url: str, monkeypatch,
) -> None:
    import liquent_platform.persistence.database as database

    calls: list[object] = []
    monkeypatch.setattr(
        database, "create_engine", lambda *_args, **_kwargs: calls.append(True),
    )
    monkeypatch.setattr(
        database, "_configure_sqlite_adapters",
        lambda: pytest.fail("authority check must precede adapters"),
    )

    with pytest.raises(ValueError) as raised:
        database.build_engine(database_url)

    assert raised.value.args == ("unsupported_database_url_authority",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert "do-not-disclose" not in str(raised.value)
    assert calls == []


def test_sqlite_authority_rejection_precedes_query_policy(monkeypatch) -> None:
    import liquent_platform.persistence.database as database

    monkeypatch.setattr(
        database, "create_engine",
        lambda *_args, **_kwargs: pytest.fail("must not build"),
    )

    with pytest.raises(ValueError) as raised:
        database.build_engine(
            "sqlite://actor:secret@host/database.db?uri=true&mode=ro"
        )
    assert raised.value.args == ("unsupported_database_url_authority",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


@pytest.mark.parametrize(
    "database_url",
    ["sqlite://", "sqlite:///:memory:"],
)
def test_authority_free_memory_sqlite_remains_supported(database_url: str) -> None:
    engine = build_engine(database_url)
    try:
        assert engine.connect().scalar(text("SELECT 1")) == 1
    finally:
        engine.dispose()


def test_authority_free_file_paths_remain_supported(tmp_path) -> None:
    for path in (tmp_path / "first.db", tmp_path / "nested" / "second.db"):
        path.parent.mkdir(parents=True, exist_ok=True)
        engine = build_engine(f"sqlite:///{path}")
        try:
            assert engine.connect().scalar(text("SELECT 1")) == 1
        finally:
            engine.dispose()


def test_postgresql_authority_remains_supported(monkeypatch) -> None:
    import liquent_platform.persistence.database as database

    captured: dict[str, object] = {}
    sentinel = object()

    def capture(value: str, **options: object) -> object:
        captured.update(database_url=value, **options)
        return sentinel

    monkeypatch.setattr(database, "create_engine", capture)
    url = "postgresql+psycopg://actor:secret@database:5432/liquent"

    assert database.build_engine(url) is sentinel
    assert captured["database_url"] == url
    assert captured["connect_args"] == {"connect_timeout": 3}
