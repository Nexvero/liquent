from sqlalchemy import Engine, text
import pytest

from liquent_platform.persistence.release_publication_attempt import DatabaseReleasePublicationAttemptPreflight
from test_release_publication_attempt import ATTEMPT, EXECUTION, EXECUTOR, HANDOFF, PUBLISHER, CHANNEL, REVISION, NOW, seed


pytestmark = pytest.mark.postgres_integration


def test_postgresql_atomically_prepares_one_attempt(postgres_engine: Engine):
    with postgres_engine.begin() as connection:
        seed(connection)
    result = DatabaseReleasePublicationAttemptPreflight(
        postgres_engine, executor_id=EXECUTOR,
        generate_attempt_id=lambda: ATTEMPT, clock=lambda: NOW,
    ).prepare_attempt(EXECUTION, HANDOFF, PUBLISHER, CHANNEL, REVISION)
    assert result is not None
    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT (SELECT count(*) FROM release_publication_executions),"
            "(SELECT count(*) FROM release_publication_execution_attempts),"
            "(SELECT count(*) FROM release_publication_receipts)"
        )).one() == (1, 1, 0)
