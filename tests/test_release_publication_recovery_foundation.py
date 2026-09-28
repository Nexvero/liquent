from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


@pytest.fixture
def engine(tmp_path: Path):
    database = build_engine(f"sqlite:///{tmp_path / 'recovery-foundation.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def test_recovery_foundation_is_empty(engine: Engine):
    assert "release_publication_recovery_decisions" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM release_publication_recovery_decisions"
        )) == 0


def test_recovery_requires_known_execution_attempt_and_valid_evidence(engine: Engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO release_publication_recovery_decisions VALUES "
                "(X'72',X'65',X'61','absence_confirmed',1,NULL,NULL,NULL,CURRENT_TIMESTAMP)"
            ))
