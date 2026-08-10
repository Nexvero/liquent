from pathlib import Path

from sqlalchemy import text

from liquent_platform.persistence.database import DatabaseReadinessProbe, build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.migrations import expected_head


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def test_migration_history_has_one_unambiguous_head() -> None:
    # Moves with each additive revision; the point is that exactly one head
    # exists, not which one. LQ-180 added the identity and admission tables.
    assert expected_head() == "20260811_0002"


def test_migration_history_is_declared_as_packaged_artifact_data() -> None:
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert '"persistence/alembic/versions/*.py"' in pyproject


def test_upgrade_establishes_current_revision_and_readiness(tmp_path: Path) -> None:
    url = _sqlite_url(tmp_path / "current.db")
    upgrade_to_head(url)
    engine = build_engine(url)
    try:
        assert DatabaseReadinessProbe(engine).check().ready is True
        with engine.connect() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
        assert revision == expected_head()
    finally:
        engine.dispose()


def test_empty_database_is_not_ready(tmp_path: Path) -> None:
    engine = build_engine(_sqlite_url(tmp_path / "empty.db"))
    try:
        readiness = DatabaseReadinessProbe(engine).check()
        assert readiness.ready is False
        assert readiness.reason == "schema_revision_mismatch"
    finally:
        engine.dispose()


def test_stale_or_unknown_revision_is_not_ready(tmp_path: Path) -> None:
    url = _sqlite_url(tmp_path / "stale.db")
    upgrade_to_head(url)
    engine = build_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num='stale_revision'"))
        readiness = DatabaseReadinessProbe(engine).check()
        assert readiness.ready is False
        assert readiness.reason == "schema_revision_mismatch"
    finally:
        engine.dispose()


def test_unreachable_database_is_not_ready() -> None:
    engine = build_engine("postgresql+psycopg://liquent:x@127.0.0.1:1/liquent")
    try:
        readiness = DatabaseReadinessProbe(engine).check()
        assert readiness.ready is False
        assert readiness.reason == "database_unavailable"
    finally:
        engine.dispose()
