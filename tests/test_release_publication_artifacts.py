from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tarfile

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_authority import ReleasePromotionVerifierId
from liquent_platform.identity.release_publication import (
    ReleasePublicationArtifactBinding,
    ReleasePublicationAttemptId,
    ReleasePublicationExecutionId,
    ReleasePublicationHandoffId,
    VerifiedReleasePublicationArtifacts,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationArtifactIntegrityUnavailable,
    ReleasePublicationArtifactSourceUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.release_publication_artifacts import (
    BoundLocalReleasePublicationArtifactSource,
    DatabaseReleasePublicationArtifactIntegrityCheck,
    ReleasePublicationArtifactFiles,
)
from liquent_platform.persistence.release_registry_projection import (
    DatabaseCurrentReleaseAuthorityRegistryProjection,
)
from test_release_promotion_verifier import AUTHORITY_ID, KEY_ID, DECISION_TIME, signed_candidate
from tools.release_promotion_verifier import verify_release_promotion


EXECUTION = ReleasePublicationExecutionId("execution-255")
ATTEMPT = ReleasePublicationAttemptId("attempt-255")
HANDOFF = ReleasePublicationHandoffId("handoff-255")


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _wheel_hash(path: Path) -> str:
    with tarfile.open(path, "r:gz") as archive:
        member = next(item for item in archive.getmembers() if item.name.endswith("/manifest.json"))
        opened = archive.extractfile(member)
        assert opened is not None
        return json.loads(opened.read())["wheel"]["sha256"]


def seed_prepared(connection, candidate, evidence_path: Path, evidence: dict[str, object]):
    values = {
        "signer": AUTHORITY_ID.encode(), "key": KEY_ID.encode(),
        "lifecycle": b"lifecycle-255",
        "registry": b"registry-255", "policy": str(evidence["policy_revision"]).encode(),
        "publisher": b"publisher-255", "channel": b"channel-255",
        "channel_revision": b"channel-revision-255", "executor": b"executor-255",
        "handoff": HANDOFF.value.encode(), "execution": EXECUTION.value.encode(),
        "attempt": ATTEMPT.value.encode(), "decision": b"decision-255",
        "verifier": str(evidence["verification_identity"]).encode(),
        "bundle": _hash(candidate["bundle"].read_bytes()),
        "wheel": _wheel_hash(candidate["bundle"]),
        "checksums": evidence["checksums_sha256"],
        "signature": _hash(candidate["signature"].read_bytes()),
        "evidence": _hash(evidence_path.read_bytes()),
        "commit": evidence["source_commit"], "version": evidence["package_version"],
        "format": evidence["bundle_format_version"], "promotion_time": DECISION_TIME,
        "now": datetime(2026, 8, 18, 19, tzinfo=timezone.utc),
        "fingerprint": candidate["fingerprint"], "public_key": candidate["public_key"],
    }
    connection.execute(text("INSERT INTO release_signer_authorities VALUES (:signer)"), values)
    connection.execute(text("INSERT INTO release_registry_lifecycle_authorities VALUES (:lifecycle)"), values)
    connection.execute(text(
        "INSERT INTO release_signing_keys VALUES "
        "(:key,:signer,'ssh-ed25519','liquent-operations-release-v1',:fingerprint,:public_key)"
    ), values)
    connection.execute(text("INSERT INTO release_registry_set_revisions VALUES (:registry,:policy,'active')"), values)
    connection.execute(text("INSERT INTO release_registry_revision_signers VALUES (:registry,:signer,'active')"), values)
    connection.execute(text("INSERT INTO release_registry_revision_lifecycle_authorities VALUES (:registry,:lifecycle,'active')"), values)
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
    connection.execute(text("INSERT INTO release_publication_current_channels VALUES (:channel,:channel_revision)"), values)
    connection.execute(text("INSERT INTO release_publication_executors VALUES (:executor)"), values)
    connection.execute(text(
        "INSERT INTO release_publication_handoffs VALUES "
        "(:handoff,:decision,:publisher,:channel,:channel_revision,:bundle,:wheel,"
        ":checksums,:signature,:evidence,:commit,:version,:format,:signer,:key,"
        ":registry,:policy,:verifier,:promotion_time,:now,'ready_for_publication')"
    ), values)
    connection.execute(text(
        "INSERT INTO release_publication_executions VALUES "
        "(:execution,:handoff,:executor,:publisher,:channel,:channel_revision,"
        ":bundle,:signature,'prepared',:now)"
    ), values)
    connection.execute(text(
        "INSERT INTO release_publication_execution_attempts VALUES "
        "(:attempt,:execution,1,'prepared',:now,NULL)"
    ), values)
    return values


@pytest.fixture
def ready(tmp_path: Path, signed_candidate):
    evidence = verify_release_promotion(
        bundle_path=signed_candidate["bundle"], signature_path=signed_candidate["signature"],
        registry_path=signed_candidate["registry"], key_id=KEY_ID, clock=lambda: DECISION_TIME,
    )
    evidence_path = tmp_path / "promotion.json"
    evidence_path.write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n")
    engine = build_engine(f"sqlite:///{tmp_path / 'artifacts.db'}")
    upgrade_to_head(str(engine.url))
    with engine.begin() as connection:
        values = seed_prepared(connection, signed_candidate, evidence_path, evidence)
    binding = ReleasePublicationArtifactBinding(
        HANDOFF, values["bundle"], values["signature"], values["evidence"]
    )
    files = ReleasePublicationArtifactFiles(
        signed_candidate["bundle"], signed_candidate["signature"], evidence_path
    )
    projection = DatabaseCurrentReleaseAuthorityRegistryProjection(
        engine, verification_identity=ReleasePromotionVerifierId(str(evidence["verification_identity"]))
    )
    try:
        yield engine, signed_candidate, evidence_path, binding, files, projection
    finally:
        engine.dispose()


def checker(ready, source=None):
    engine, _candidate, _evidence, binding, files, projection = ready
    return DatabaseReleasePublicationArtifactIntegrityCheck(
        engine, artifact_source=source or BoundLocalReleasePublicationArtifactSource({binding: files}),
        registry_projection=projection, clock=lambda: DECISION_TIME,
    )


def test_prepared_attempt_verifies_all_bytes_and_current_signature(ready):
    result = checker(ready).verify_artifacts(EXECUTION, ATTEMPT)
    assert type(result) is VerifiedReleasePublicationArtifacts
    assert result.handoff_id == HANDOFF
    assert result.package_version == "1.2.3"
    assert result.bundle_sha256 == ready[3].bundle_sha256


def test_mutated_bound_artifact_is_neutrally_rejected(ready):
    ready[1]["bundle"].write_bytes(ready[1]["bundle"].read_bytes() + b"changed")
    assert checker(ready).verify_artifacts(EXECUTION, ATTEMPT) is None


def test_historical_evidence_mismatch_is_neutrally_rejected(ready):
    evidence = json.loads(ready[2].read_text())
    evidence["package_version"] = "9.9.9"
    value = (json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ready[2].write_bytes(value)
    with ready[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_publication_handoffs SET promotion_evidence_sha256=:value"
        ), {"value": _hash(value)})
    binding = ReleasePublicationArtifactBinding(
        HANDOFF, ready[3].bundle_sha256, ready[3].signature_sha256, _hash(value)
    )
    source = BoundLocalReleasePublicationArtifactSource({binding: ready[4]})
    assert checker(ready, source).verify_artifacts(EXECUTION, ATTEMPT) is None


def test_current_key_revocation_blocks_later_integrity_decision(ready):
    with ready[0].begin() as connection:
        connection.execute(text("UPDATE release_registry_revision_keys SET status='revoked'"))
    assert checker(ready).verify_artifacts(EXECUTION, ATTEMPT) is None


def test_unknown_attempt_is_neutral_without_source_access(ready):
    class Broken:
        def load_artifacts(self, binding): raise AssertionError("must not load")
    assert checker(ready, Broken()).verify_artifacts(
        EXECUTION, ReleasePublicationAttemptId("unknown")
    ) is None


def test_source_rejects_unbound_or_symlinked_locations(ready, tmp_path: Path):
    source = BoundLocalReleasePublicationArtifactSource({ready[3]: ready[4]})
    with pytest.raises(ReleasePublicationArtifactSourceUnavailable):
        source.load_artifacts(ReleasePublicationArtifactBinding(
            ReleasePublicationHandoffId("other"), ready[3].bundle_sha256,
            ready[3].signature_sha256, ready[3].promotion_evidence_sha256,
        ))
    link = tmp_path / "linked-bundle"
    link.symlink_to(ready[1]["bundle"])
    linked = ReleasePublicationArtifactFiles(link, ready[4].signature_path, ready[2])
    with pytest.raises(ReleasePublicationArtifactSourceUnavailable):
        BoundLocalReleasePublicationArtifactSource({ready[3]: linked}).load_artifacts(ready[3])


def test_corrupt_execution_binding_is_technical_unavailability(ready):
    with ready[0].begin() as connection:
        connection.execute(text(
            "UPDATE release_publication_executions SET bundle_sha256=:value"
        ), {"value": "0" * 64})
    with pytest.raises(ReleasePublicationArtifactIntegrityUnavailable):
        checker(ready).verify_artifacts(EXECUTION, ATTEMPT)
