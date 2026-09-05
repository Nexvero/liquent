from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


TABLES = (
    "release_publication_executors",
    "release_publication_executions",
    "release_publication_execution_attempts",
    "release_publication_receipt_reconciliations",
    "release_publication_execution_reassessments",
)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'execution.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def test_execution_foundation_is_completely_empty(engine: Engine):
    assert set(TABLES) <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert all(connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0
                   for table in TABLES)


def test_execution_requires_known_handoff_executor_and_channel(engine: Engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO release_publication_executions VALUES "
                "(X'65',X'68',X'78',X'70',X'63',X'72','bundle','signature',"
                "'prepared',CURRENT_TIMESTAMP)"
            ))


def test_attempt_requires_known_execution_and_positive_number(engine: Engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO release_publication_execution_attempts VALUES "
                "(X'61',X'65',1,'prepared',CURRENT_TIMESTAMP,NULL)"
            ))


def test_reconciliation_requires_receipt_execution_and_attempt(engine: Engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO release_publication_receipt_reconciliations VALUES "
                "(X'72',X'65',X'61',X'69',X'76',CURRENT_TIMESTAMP,'published')"
            ))
