from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_publication import (
    BootstrappedReleasePublicationControlPlane,
    ReleasePublicationBootstrapId,
    ReleasePublicationChannelDefinition,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublisherAuthorityId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationBootstrapConflict,
    ReleasePublicationBootstrapUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.release_publication_bootstrap import (
    DatabaseInitialReleasePublicationControlPlaneBootstrap,
)


BOOTSTRAP = ReleasePublicationBootstrapId("bootstrap-250")
DEFINITION = ReleasePublicationChannelDefinition("liquent", "package-index", "stable")
RESULT = BootstrappedReleasePublicationControlPlane(
    BOOTSTRAP, ReleasePublisherAuthorityId("publisher-250"),
    ReleasePublicationChannelId("channel-250"),
    ReleasePublicationChannelPolicyRevisionId("revision-250"),
)


class Source:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'bootstrap.db'}")

    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _store(engine, sources=None):
    values = sources or [
        Source(RESULT.publisher_authority_id), Source(RESULT.channel_id),
        Source(RESULT.channel_revision_id),
    ]
    return DatabaseInitialReleasePublicationControlPlaneBootstrap(
        engine, generate_publisher_authority_id=values[0],
        generate_channel_id=values[1], generate_channel_revision_id=values[2],
    )


def test_bootstrap_creates_exact_active_channel_without_handoff(engine: Engine):
    assert _store(engine).bootstrap(BOOTSTRAP, DEFINITION) == RESULT
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT revision.status,revision.artifact_class,publisher.status,"
            "revision.package_name,revision.provider_kind,revision.target_name "
            "FROM release_publication_current_channels AS current "
            "JOIN release_publication_channel_revisions AS revision "
            "ON revision.revision_id=current.revision_id "
            "AND revision.channel_id=current.channel_id "
            "JOIN release_publication_revision_publishers AS publisher "
            "ON publisher.revision_id=revision.revision_id"
        )).one() == (
            "active", "operational_bundle", "active", "liquent",
            "package-index", "stable",
        )
        assert connection.execute(text(
            "SELECT (SELECT count(*) FROM release_publication_handoffs),"
            "(SELECT count(*) FROM release_publication_receipts),"
            "(SELECT count(*) FROM release_publication_reassessments)"
        )).one() == (0, 0, 0)


def test_exact_retry_returns_same_ids_without_generation(engine: Engine):
    assert _store(engine).bootstrap(BOOTSTRAP, DEFINITION) == RESULT
    sources = [Source(RuntimeError("must not draw")) for _ in range(3)]
    assert _store(engine, sources).bootstrap(BOOTSTRAP, DEFINITION) == RESULT
    assert [source.calls for source in sources] == [0, 0, 0]


def test_same_id_with_other_definition_is_conflict(engine: Engine):
    assert _store(engine).bootstrap(BOOTSTRAP, DEFINITION) == RESULT
    with pytest.raises(ReleasePublicationBootstrapConflict):
        _store(engine).bootstrap(
            BOOTSTRAP,
            ReleasePublicationChannelDefinition("liquent", "package-index", "beta"),
        )


def test_other_id_or_partial_history_closes_without_generation(engine: Engine):
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO release_publication_channels VALUES (X'63')"
        ))
    sources = [Source(RuntimeError("must not draw")) for _ in range(3)]
    assert _store(engine, sources).bootstrap(BOOTSTRAP, DEFINITION) is None
    assert [source.calls for source in sources] == [0, 0, 0]


@pytest.mark.parametrize("index", range(3))
def test_generator_failure_rolls_back_every_fact(engine: Engine, index: int):
    values = [RESULT.publisher_authority_id, RESULT.channel_id, RESULT.channel_revision_id]
    sources = [Source(value) for value in values]
    sources[index] = Source(RuntimeError("generator detail"))
    with pytest.raises(ReleasePublicationBootstrapUnavailable):
        _store(engine, sources).bootstrap(BOOTSTRAP, DEFINITION)
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT (SELECT count(*) FROM release_publication_channels),"
            "(SELECT count(*) FROM release_publisher_authorities),"
            "(SELECT count(*) FROM release_publication_bootstraps)"
        )).one() == (0, 0, 0)


def test_invalid_input_is_detail_free(engine: Engine):
    with pytest.raises(ReleasePublicationBootstrapUnavailable) as raised:
        _store(engine).bootstrap("bad", DEFINITION)
    assert raised.value.args == ("release_publication_bootstrap_unavailable",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
