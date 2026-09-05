from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_publication import (
    ReleasePublicationExecutorId,
    ReleasePublicationExecutorRegistrationId,
)
from liquent_platform.persistence.release_publication_executor_registration import (
    DatabaseReleasePublicationExecutorRegistration,
)


pytestmark = pytest.mark.postgres_integration


def test_concurrent_exact_retry_commits_one_executor_and_one_binding(
    postgres_engine: Engine,
):
    registration_id = ReleasePublicationExecutorRegistrationId("registration-1")

    def run(suffix: str):
        store = DatabaseReleasePublicationExecutorRegistration(
            postgres_engine,
            generate_executor_id=lambda: ReleasePublicationExecutorId(
                f"executor-{suffix}"
            ),
        )
        return store.register(registration_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run, ("one", "two")))

    assert results[0] == results[1]
    with postgres_engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT (SELECT count(*) FROM release_publication_executors),"
                " (SELECT count(*) FROM release_publication_executor_registrations)"
            )
        ).one() == (1, 1)
