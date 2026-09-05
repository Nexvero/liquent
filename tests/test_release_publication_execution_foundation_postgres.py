import pytest
from sqlalchemy import Engine, inspect, text


pytestmark = pytest.mark.postgres_integration


def test_postgresql_execution_foundation_is_empty(postgres_engine: Engine):
    tables = {
        "release_publication_executors",
        "release_publication_executions",
        "release_publication_execution_attempts",
        "release_publication_receipt_reconciliations",
        "release_publication_execution_reassessments",
    }
    assert tables <= set(inspect(postgres_engine).get_table_names())
    with postgres_engine.connect() as connection:
        assert all(connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0
                   for table in tables)
