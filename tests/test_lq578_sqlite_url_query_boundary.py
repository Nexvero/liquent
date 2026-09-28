import pytest


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///file:database.db?uri=true",
        "sqlite:///file:database.db?mode=memory&uri=true",
        "sqlite:///file:database.db?mode=ro&uri=true",
        "sqlite:///file:database.db?cache=shared&uri=true",
        "sqlite:///file:database.db?immutable=true&uri=true",
        "sqlite:///file:database.db?nolock=1&uri=true",
        "sqlite:///database.db?unknown=do-not-disclose",
    ],
)
def test_unsupported_sqlite_query_is_rejected_before_side_effects(
    database_url: str, monkeypatch,
) -> None:
    import liquent_platform.persistence.database as database

    calls: list[object] = []
    monkeypatch.setattr(
        database, "create_engine", lambda *_args, **_kwargs: calls.append(True),
    )
    monkeypatch.setattr(
        database, "_configure_sqlite_adapters",
        lambda: pytest.fail("query check must precede adapters"),
    )

    with pytest.raises(ValueError) as raised:
        database.build_engine(database_url)

    assert raised.value.args == ("unsupported_database_url_option",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert "do-not-disclose" not in str(raised.value)
    assert calls == []


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite://?timeout=0.001",
        "sqlite://?check_same_thread=true",
        "sqlite+pysqlite:///:memory:?timeout=99&check_same_thread=true",
    ],
)
def test_centrally_overridden_sqlite_compatibility_queries_reach_engine(
    database_url: str, monkeypatch,
) -> None:
    import liquent_platform.persistence.database as database

    captured: dict[str, object] = {}
    sentinel = object()

    def capture(value: str, **options: object) -> object:
        captured.update(database_url=value, **options)
        return sentinel

    monkeypatch.setattr(database, "create_engine", capture)
    monkeypatch.setattr(database.event, "listen", lambda *_args: None)

    assert database.build_engine(database_url) is sentinel
    assert captured["connect_args"] == {
        "check_same_thread": False,
        "timeout": 5,
    }


def test_postgresql_query_options_remain_outside_sqlite_policy(monkeypatch) -> None:
    import liquent_platform.persistence.database as database

    captured: dict[str, object] = {}
    sentinel = object()

    def capture(value: str, **options: object) -> object:
        captured.update(database_url=value, **options)
        return sentinel

    monkeypatch.setattr(database, "create_engine", capture)
    url = (
        "postgresql+psycopg://actor:secret@database/liquent"
        "?sslmode=require&application_name=liquent"
    )

    assert database.build_engine(url) is sentinel
    assert captured["database_url"] == url
    assert captured["connect_args"] == {"connect_timeout": 3}


def test_backend_and_driver_rejections_precede_sqlite_query_policy(monkeypatch) -> None:
    import liquent_platform.persistence.database as database

    monkeypatch.setattr(
        database, "create_engine",
        lambda *_args, **_kwargs: pytest.fail("must not build"),
    )

    with pytest.raises(ValueError) as backend:
        database.build_engine("mysql+pymysql://database/liquent?uri=true")
    assert backend.value.args == ("unsupported_database_backend",)

    with pytest.raises(ValueError) as driver:
        database.build_engine("sqlite+aiosqlite:///:memory:?uri=true")
    assert driver.value.args == ("unsupported_database_driver",)
