import pytest
from sqlalchemy import Engine, inspect, text


pytestmark = pytest.mark.postgres_integration


def test_postgresql_recovery_foundation_is_empty(postgres_engine: Engine):
    assert "release_publication_recovery_decisions" in inspect(postgres_engine).get_table_names()
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_recovery_decisions"
        )) == 0
