from datetime import date, datetime, timezone
import warnings

from sqlalchemy import text

from liquent_platform.persistence.database import build_engine


def test_explicit_adapters_preserve_iso_values_without_python_312_warning(
    tmp_path,
) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        engine = build_engine(f"sqlite:///{tmp_path / 'explicit-adapters.db'}")
        try:
            with engine.begin() as connection:
                connection.execute(text(
                    "CREATE TABLE facts (day TEXT NOT NULL, observed_at TEXT NOT NULL)"
                ))
                connection.execute(
                    text("INSERT INTO facts VALUES (:day,:observed_at)"),
                    {
                        "day": date(2026, 8, 27),
                        "observed_at": datetime(
                            2026, 8, 27, 12, 34, 56, 789, tzinfo=timezone.utc
                        ),
                    },
                )
                row = connection.execute(text(
                    "SELECT day,observed_at FROM facts"
                )).one()
        finally:
            engine.dispose()
    assert row.day == "2026-08-27"
    assert row.observed_at == "2026-08-27 12:34:56.000789+00:00"


def test_postgresql_engine_build_does_not_configure_sqlite(monkeypatch) -> None:
    import liquent_platform.persistence.database as database

    monkeypatch.setattr(
        database, "_configure_sqlite_adapters",
        lambda: (_ for _ in ()).throw(AssertionError("sqlite-only")),
    )
    engine = database.build_engine(
        "postgresql+psycopg://liquent:secret@127.0.0.1:1/liquent"
    )
    engine.dispose()
