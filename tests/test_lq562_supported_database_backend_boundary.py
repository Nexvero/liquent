import pytest

from liquent_platform.persistence.database import build_engine


@pytest.mark.parametrize(
    "database_url",
    [
        "mysql+pymysql://actor:do-not-disclose@database/liquent",
        "oracle://actor:do-not-disclose@database/liquent",
        "mssql+pyodbc://actor:do-not-disclose@database/liquent",
    ],
)
def test_unsupported_backend_is_rejected_before_engine_build(
    database_url: str, monkeypatch,
) -> None:
    import liquent_platform.persistence.database as database

    calls: list[object] = []
    monkeypatch.setattr(
        database, "create_engine", lambda *_args, **_kwargs: calls.append(True),
    )

    with pytest.raises(ValueError) as raised:
        database.build_engine(database_url)

    assert raised.value.args == ("unsupported_database_backend",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert "do-not-disclose" not in str(raised.value)
    assert calls == []


@pytest.mark.parametrize(
    "database_url",
    ["not a database url", "secret-do-not-disclose"],
)
def test_malformed_url_is_rejected_without_parser_or_secret_detail(
    database_url: str, monkeypatch,
) -> None:
    import liquent_platform.persistence.database as database

    calls: list[object] = []
    monkeypatch.setattr(
        database, "create_engine", lambda *_args, **_kwargs: calls.append(True),
    )

    with pytest.raises(ValueError) as raised:
        database.build_engine(database_url)

    assert raised.value.args == ("invalid_database_url",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert "secret" not in str(raised.value)
    assert calls == []


@pytest.mark.parametrize(
    "database_url,backend",
    [
        ("sqlite://", "sqlite"),
        ("sqlite+pysqlite:///:memory:", "sqlite"),
        ("postgresql+psycopg://actor:secret@127.0.0.1:1/liquent", "postgresql"),
    ],
)
def test_supported_backend_reaches_engine_factory(
    database_url: str, backend: str, monkeypatch,
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
    assert backend in database_url


def test_non_string_url_is_detail_free_invalid_input(monkeypatch) -> None:
    import liquent_platform.persistence.database as database

    monkeypatch.setattr(
        database, "create_engine",
        lambda *_args, **_kwargs: pytest.fail("must not build"),
    )

    with pytest.raises(ValueError) as raised:
        database.build_engine(None)  # type: ignore[arg-type]
    assert raised.value.args == ("invalid_database_url",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
