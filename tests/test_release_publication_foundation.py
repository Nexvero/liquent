from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.identity.release_publication import (
    ReleasePublicationChannelId,
    ReleasePublicationBootstrapId,
    ReleasePublicationAttemptId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationDecisionId,
    ReleasePublicationExecutionId,
    ReleasePublicationExecutorId,
    ReleasePublicationHandoffId,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationRecoveryId,
    ReleasePublisherAuthorityId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


IDENTIFIERS = (
    ReleasePublicationAttemptId,
    ReleasePublicationExecutionId,
    ReleasePublicationExecutorId,
    ReleasePublicationBootstrapId,
    ReleasePublicationHandoffId,
    ReleasePublisherAuthorityId,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationDecisionId,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationRecoveryId,
)
TABLES = (
    "release_publication_channels",
    "release_publisher_authorities",
    "release_publication_channel_revisions",
    "release_publication_revision_publishers",
    "release_publication_current_channels",
    "release_publication_handoffs",
    "release_publication_receipts",
    "release_publication_reassessments",
)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'publication.db'}")

    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


@pytest.mark.parametrize("kind", IDENTIFIERS)
def test_publication_identifiers_are_stable_slotted_and_repr_free(kind):
    identifier = kind("opaque-249")
    assert [item.name for item in fields(kind)] == ["value"]
    assert "opaque-249" not in repr(identifier)
    assert not hasattr(identifier, "__dict__")
    with pytest.raises(FrozenInstanceError):
        identifier.value = "other"


@pytest.mark.parametrize("kind", IDENTIFIERS)
@pytest.mark.parametrize("value", ["", None, 1, b"bytes", True])
def test_publication_identifiers_reject_invalid_values(kind, value):
    with pytest.raises(ValueError):
        kind(value)


def test_secure_material_draws_independent_publication_identifiers(monkeypatch):
    values = iter(f"publication-{index}" for index in range(12))
    monkeypatch.setattr("secrets.token_urlsafe", lambda _: next(values))
    material = SecureIdentityAuthorityMaterialGenerator()
    generated = (
        material.new_release_publication_attempt_id(),
        material.new_release_publication_execution_id(),
        material.new_release_publication_executor_id(),
        material.new_release_publication_bootstrap_id(),
        material.new_release_publication_handoff_id(),
        material.new_release_publisher_authority_id(),
        material.new_release_publication_channel_id(),
        material.new_release_publication_channel_policy_revision_id(),
        material.new_release_publication_decision_id(),
        material.new_release_publication_provider_receipt_id(),
        material.new_release_publication_reassessment_id(),
        material.new_release_publication_recovery_id(),
    )
    assert tuple(item.value for item in generated) == tuple(
        f"publication-{index}" for index in range(12)
    )


def test_migration_creates_only_empty_publication_inventories(engine: Engine):
    assert set(TABLES) <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert all(
            connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0
            for table in TABLES
        )


def test_current_channel_must_reference_same_channel_revision(engine: Engine):
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO release_publication_channels VALUES (X'61'),(X'62')"
        ))
        connection.execute(text(
            "INSERT INTO release_publication_channel_revisions VALUES "
            "(X'72',X'61','active','operational_bundle','liquent','index','stable')"
        ))
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO release_publication_current_channels VALUES (X'62',X'72')"
            ))


def test_receipt_and_reassessment_require_known_handoff(engine: Engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO release_publication_receipts VALUES "
                "(X'72',X'68',X'70','hash',CURRENT_TIMESTAMP)"
            ))
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO release_publication_reassessments VALUES "
                "(X'72',X'68','reassess','pending',CURRENT_TIMESTAMP)"
            ))
