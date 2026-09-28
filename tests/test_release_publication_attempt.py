from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_publication import (
    PreparedReleasePublicationAttempt,
    ReleasePublicationAttemptId,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationExecutionId,
    ReleasePublicationExecutorId,
    ReleasePublicationHandoffId,
    ReleasePublisherAuthorityId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import ReleasePublicationAttemptConflict
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.release_publication_attempt import (
    DatabaseReleasePublicationAttemptPreflight,
)


EXECUTION = ReleasePublicationExecutionId("execution-254")
ATTEMPT = ReleasePublicationAttemptId("attempt-254")
EXECUTOR = ReleasePublicationExecutorId("executor-254")
HANDOFF = ReleasePublicationHandoffId("handoff-254")
PUBLISHER = ReleasePublisherAuthorityId("publisher-254")
CHANNEL = ReleasePublicationChannelId("channel-254")
REVISION = ReleasePublicationChannelPolicyRevisionId("channel-revision-254")
NOW = datetime(2026, 8, 18, 18, tzinfo=timezone.utc)


def seed(connection) -> None:
    values = {
        "signer": b"signer-254", "key": b"key-254", "registry": b"registry-254",
        "policy": b"policy-254", "publisher": PUBLISHER.value.encode(),
        "channel": CHANNEL.value.encode(), "channel_revision": REVISION.value.encode(),
        "executor": EXECUTOR.value.encode(), "handoff": HANDOFF.value.encode(),
        "decision": b"decision-254", "verifier": b"verifier-254",
    }
    connection.execute(text("INSERT INTO release_signer_authorities VALUES (:signer)"), values)
    connection.execute(text(
        "INSERT INTO release_signing_keys VALUES "
        "(:key,:signer,'ssh-ed25519','liquent-operations-release-v1','fingerprint-254','public-key-254')"
    ), values)
    connection.execute(text("INSERT INTO release_registry_set_revisions VALUES (:registry,:policy,'active')"), values)
    connection.execute(text("INSERT INTO release_registry_revision_signers VALUES (:registry,:signer,'active')"), values)
    connection.execute(text("INSERT INTO release_registry_revision_keys VALUES (:registry,:key,:signer,'active')"), values)
    connection.execute(text("INSERT INTO release_registry_current_set VALUES (1,:registry)"), values)
    connection.execute(text("INSERT INTO release_publication_channels VALUES (:channel)"), values)
    connection.execute(text("INSERT INTO release_publisher_authorities VALUES (:publisher)"), values)
    connection.execute(text(
        "INSERT INTO release_publication_channel_revisions VALUES "
        "(:channel_revision,:channel,'active','operational_bundle','liquent','package-index','stable')"
    ), values)
    connection.execute(text(
        "INSERT INTO release_publication_revision_publishers VALUES "
        "(:channel_revision,:channel,:publisher,'active')"
    ), values)
    connection.execute(text(
        "INSERT INTO release_publication_current_channels VALUES (:channel,:channel_revision)"
    ), values)
    connection.execute(text("INSERT INTO release_publication_executors VALUES (:executor)"), values)
    connection.execute(text(
        "INSERT INTO release_publication_handoffs VALUES "
        "(:handoff,:decision,:publisher,:channel,:channel_revision,"
        ":bundle,:wheel,:checksums,:signature,:evidence,'aabbccddeeff00112233445566778899aabbccdd',"
        "'1.0.0',1,:signer,:key,:registry,:policy,:verifier,:now,:now,'ready_for_publication')"
    ), {**values, "bundle": "1" * 64, "wheel": "2" * 64,
        "checksums": "3" * 64, "signature": "4" * 64,
        "evidence": "5" * 64, "now": NOW})


@pytest.fixture
def engine(tmp_path: Path):
    database = build_engine(f"sqlite:///{tmp_path / 'attempt.db'}")
    upgrade_to_head(str(database.url))
    with database.begin() as connection:
        seed(connection)
    try:
        yield database
    finally:
        database.dispose()


def store(engine: Engine, generate=lambda: ATTEMPT):
    return DatabaseReleasePublicationAttemptPreflight(
        engine, executor_id=EXECUTOR, generate_attempt_id=generate, clock=lambda: NOW,
    )


def prepare(subject, **changes):
    values = dict(execution_id=EXECUTION, handoff_id=HANDOFF,
                  publisher_authority_id=PUBLISHER, channel_id=CHANNEL,
                  expected_channel_revision=REVISION)
    values.update(changes)
    return subject.prepare_attempt(**values)


def test_current_authority_atomically_prepares_execution_and_attempt(engine: Engine):
    assert prepare(store(engine)) == PreparedReleasePublicationAttempt(EXECUTION, ATTEMPT, HANDOFF, 1)
    with engine.connect() as connection:
        execution = connection.execute(text(
            "SELECT status,bundle_sha256,signature_sha256 FROM release_publication_executions"
        )).one()
        attempt = connection.execute(text(
            "SELECT attempt_number,status,finished_at FROM release_publication_execution_attempts"
        )).one()
        assert execution == ("prepared", "1" * 64, "4" * 64)
        assert attempt == (1, "prepared", None)
        assert connection.scalar(text("SELECT count(*) FROM release_publication_receipts")) == 0


def test_exact_retry_returns_same_attempt_without_new_material(engine: Engine):
    first = prepare(store(engine))
    assert prepare(store(engine, lambda: (_ for _ in ()).throw(RuntimeError()))) == first


def test_reused_execution_or_handoff_with_different_binding_conflicts(engine: Engine):
    assert prepare(store(engine)) is not None
    with pytest.raises(ReleasePublicationAttemptConflict):
        prepare(store(engine), publisher_authority_id=ReleasePublisherAuthorityId("other"))
    with pytest.raises(ReleasePublicationAttemptConflict):
        prepare(store(engine), execution_id=ReleasePublicationExecutionId("other"))


@pytest.mark.parametrize("statement", [
    "UPDATE release_publication_revision_publishers SET status='inactive'",
    "UPDATE release_registry_revision_keys SET status='revoked'",
    "UPDATE release_registry_revision_signers SET status='inactive'",
    "UPDATE release_publication_channel_revisions SET status='inactive'",
])
def test_revoked_current_authority_is_neutral_and_creates_nothing(engine: Engine, statement: str):
    with engine.begin() as connection:
        connection.execute(text(statement))
    assert prepare(store(engine)) is None
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM release_publication_executions")) == 0


def test_pending_reassessment_or_existing_receipt_blocks_preflight(engine: Engine):
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO release_publication_reassessments VALUES "
            "(X'72',:handoff,'reassess','pending',:now)"
        ), {"handoff": HANDOFF.value.encode(), "now": NOW})
    assert prepare(store(engine)) is None
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM release_publication_reassessments"))
        connection.execute(text(
            "INSERT INTO release_publication_receipts VALUES "
            "(:receipt,:handoff,:provider,:bundle,:now)"
        ), {"receipt": b"receipt-254", "handoff": HANDOFF.value.encode(),
            "provider": b"provider-receipt-254", "bundle": "1" * 64,
            "now": NOW})
    assert prepare(store(engine)) is None


def test_malformed_persisted_hash_is_technical_unavailability(engine: Engine):
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE release_publication_handoffs SET wheel_sha256='invalid'"
        ))
    from liquent_platform.persistence.identity_errors import ReleasePublicationAttemptUnavailable
    with pytest.raises(ReleasePublicationAttemptUnavailable):
        prepare(store(engine))
