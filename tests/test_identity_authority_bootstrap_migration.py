from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


@pytest.fixture
def engine(tmp_path: Path):
    built = build_engine(f"sqlite:///{tmp_path / 'bootstrap.db'}")
    upgrade_to_head(built.url.render_as_string(hide_password=False))
    with built.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
    yield built
    built.dispose()


def test_migration_adds_one_empty_restrictive_singleton_table(engine: object) -> None:
    inspector = inspect(engine)
    assert "identity_authority_bootstrap_decisions" in inspector.get_table_names()
    assert inspector.get_pk_constraint("identity_authority_bootstrap_decisions")[
        "constrained_columns"
    ] == ["singleton_key"]
    foreign_keys = inspector.get_foreign_keys(
        "identity_authority_bootstrap_decisions"
    )
    assert [
        (item["referred_table"], item["options"]["ondelete"])
        for item in foreign_keys
    ] == [("identity_admissions", "RESTRICT")]
    with engine.connect() as connection:  # type: ignore[union-attr]
        assert connection.scalar(
            text("SELECT count(*) FROM identity_authority_bootstrap_decisions")
        ) == 0


def test_singleton_key_and_admission_reference_are_enforced(engine: object) -> None:
    statement = text(
        "INSERT INTO identity_authority_bootstrap_decisions VALUES (:key, :admission)"
    )
    for values in [
        {"key": 2, "admission": b"missing"},
        {"key": 1, "admission": b"missing"},
    ]:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:  # type: ignore[union-attr]
                connection.execute(statement, values)
