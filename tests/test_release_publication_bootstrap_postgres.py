from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_publication import (
    ReleasePublicationBootstrapId,
    ReleasePublicationChannelDefinition,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublisherAuthorityId,
)
from liquent_platform.persistence.release_publication_bootstrap import (
    DatabaseInitialReleasePublicationControlPlaneBootstrap,
)


pytestmark = pytest.mark.postgres_integration
DEFINITION = ReleasePublicationChannelDefinition("liquent", "package-index", "stable")


def _store(engine: Engine, suffix: str):
    return DatabaseInitialReleasePublicationControlPlaneBootstrap(
        engine,
        generate_publisher_authority_id=lambda: ReleasePublisherAuthorityId(f"publisher-{suffix}"),
        generate_channel_id=lambda: ReleasePublicationChannelId(f"channel-{suffix}"),
        generate_channel_revision_id=lambda: ReleasePublicationChannelPolicyRevisionId(f"revision-{suffix}"),
    )


def test_concurrent_bootstrap_commits_exactly_one_complete_control_plane(
    postgres_engine: Engine,
):
    def run(suffix):
        return _store(postgres_engine, suffix).bootstrap(
            ReleasePublicationBootstrapId(f"bootstrap-{suffix}"), DEFINITION
        )
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run, ("one", "two")))
    assert sum(result is not None for result in results) == 1
    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT (SELECT count(*) FROM release_publication_bootstraps),"
            "(SELECT count(*) FROM release_publication_channels),"
            "(SELECT count(*) FROM release_publisher_authorities),"
            "(SELECT count(*) FROM release_publication_channel_revisions),"
            "(SELECT count(*) FROM release_publication_current_channels),"
            "(SELECT count(*) FROM release_publication_handoffs)"
        )).one() == (1, 1, 1, 1, 1, 0)
