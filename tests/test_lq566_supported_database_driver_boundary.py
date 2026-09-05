import pytest


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite+aiosqlite:///:memory:",
        "sqlite+apsw:///:memory:",
        "postgresql+asyncpg://actor:do-not-disclose@database/liquent",
        "postgresql+psycopg2://actor:do-not-disclose@database/liquent",
        "postgresql://actor:do-not-disclose@database/liquent",
    ],
)
def test_unsupported_driver_is_rejected_before_engine_build(
    database_url: str, monkeypatch,
) -> None:
    import liquent_platform.persistence.database as database

    calls: list[object] = []
    monkeypatch.setattr(
        database, "create_engine", lambda *_args, **_kwargs: calls.append(True),
    )
    monkeypatch.setattr(
        database, "_configure_sqlite_adapters",
        lambda: pytest.fail("driver check must precede adapters"),
    )

    with pytest.raises(ValueError) as raised:
        database.build_engine(database_url)

    assert raised.value.args == ("unsupported_database_driver",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert "do-not-disclose" not in str(raised.value)
    assert calls == []


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite://",
        "sqlite+pysqlite:///:memory:",
        "postgresql+psycopg://actor:secret@127.0.0.1:1/liquent",
    ],
)
def test_allowlisted_driver_reaches_engine_build(
    database_url: str, monkeypatch,
) -> None:
    import liquent_platform.persistence.database as database

    sentinel = object()
    calls: list[str] = []

    def capture(value: str, **_options: object) -> object:
        calls.append(value)
        return sentinel

    monkeypatch.setattr(database, "create_engine", capture)
    monkeypatch.setattr(database.event, "listen", lambda *_args: None)

    assert database.build_engine(database_url) is sentinel
    assert calls == [database_url]


def test_backend_rejection_precedes_driver_rejection(monkeypatch) -> None:
    import liquent_platform.persistence.database as database

    monkeypatch.setattr(
        database, "create_engine",
        lambda *_args, **_kwargs: pytest.fail("must not build"),
    )

    with pytest.raises(ValueError) as raised:
        database.build_engine(
            "mysql+asyncmy://actor:do-not-disclose@database/liquent"
        )
    assert raised.value.args == ("unsupported_database_backend",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
