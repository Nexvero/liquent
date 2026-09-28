import pytest
from sqlalchemy import Engine, inspect, text


pytestmark = pytest.mark.postgres_integration


def test_postgresql_publication_foundation_is_empty(postgres_engine: Engine):
    tables = {
        "release_publication_channels",
        "release_publisher_authorities",
        "release_publication_channel_revisions",
        "release_publication_revision_publishers",
        "release_publication_current_channels",
        "release_publication_handoffs",
        "release_publication_receipts",
        "release_publication_reassessments",
    }
    assert tables <= set(inspect(postgres_engine).get_table_names())
    with postgres_engine.connect() as connection:
        assert all(
            connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0
            for table in tables
        )
