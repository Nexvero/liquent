from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_authority import (
    ReleaseActivationReviewerId,
    ReleasePolicyRevisionId,
    ReleasePromotionVerifierId,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseRegistrySetRevisionId,
    ReleaseSignerAuthorityId,
    ReleaseSigningKeyId,
    ReleaseSigningPublicKey,
)
from liquent_platform.identity.release_publication import (
    AcceptedReleasePublicationHandoff,
    ReleasePublicationBootstrapId,
    ReleasePublicationChannelDefinition,
    ReleasePublicationChannelId,
    ReleasePublicationChannelPolicyRevisionId,
    ReleasePublicationDecisionId,
    ReleasePublicationHandoffId,
    ReleasePublisherAuthorityId,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import ReleasePublicationHandoffConflict
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.release_key_activation import DatabaseReleaseKeyActivation
from liquent_platform.persistence.release_publication_bootstrap import DatabaseInitialReleasePublicationControlPlaneBootstrap
from liquent_platform.persistence.release_publication_handoff import DatabaseAuthorizedReleasePublicationHandoff
from liquent_platform.persistence.release_registry_bootstrap import DatabaseInitialReleaseRegistryBootstrap
from liquent_platform.persistence.release_registry_projection import DatabaseCurrentReleaseAuthorityRegistryProjection
from test_release_promotion_verifier import AUTHORITY_ID, KEY_ID, signed_candidate
from tools.release_promotion_verifier import verify_release_promotion_with_projection


HANDOFF = ReleasePublicationHandoffId("handoff-251")
DECISION = ReleasePublicationDecisionId("decision-251")
PUBLISHER = ReleasePublisherAuthorityId("publisher-251")
CHANNEL = ReleasePublicationChannelId("channel-251")
CHANNEL_REVISION = ReleasePublicationChannelPolicyRevisionId("channel-revision-251")
NOW = datetime(2026, 8, 18, 15, tzinfo=timezone.utc)


class Proof:
    def verify_proof(self, public_key, challenge, proof): return True


class Approval:
    def verify_approval(self, challenge, approval): return ReleaseActivationReviewerId("reviewer-251")


@pytest.fixture
def prepared(tmp_path: Path, signed_candidate: dict[str, object]):
    engine = build_engine(f"sqlite:///{tmp_path / 'handoff.db'}")
    upgrade_to_head(str(engine.url))
    lifecycle = ReleaseRegistryLifecycleAuthorityId("lifecycle-251")
    release_revision = ReleaseRegistrySetRevisionId("release-revision-250")
    active_revision = ReleaseRegistrySetRevisionId("release-revision-251")
    key = ReleaseSigningKeyId(KEY_ID)
    bootstrap = DatabaseInitialReleaseRegistryBootstrap(
        engine, generate_lifecycle_authority_id=lambda: lifecycle,
        generate_signer_authority_id=lambda: ReleaseSignerAuthorityId(AUTHORITY_ID),
        generate_key_id=lambda: key,
        generate_registry_revision_id=lambda: release_revision,
        generate_policy_revision_id=lambda: ReleasePolicyRevisionId("release-policy:1"),
    ).bootstrap(ReleaseRegistryBootstrapId("release-bootstrap-251"), ReleaseSigningPublicKey(
        signed_candidate["fingerprint"], signed_candidate["public_key"]
    ))
    assert bootstrap is not None
    assert DatabaseReleaseKeyActivation(
        engine, proof_verifier=Proof(), approval_verifier=Approval(),
        generate_revision_id=lambda: active_revision,
    ).activate_key(ReleaseRegistryLifecycleChangeId("activation-251"), lifecycle, key,
                   release_revision, b"proof", b"approval") is not None
    assert DatabaseInitialReleasePublicationControlPlaneBootstrap(
        engine, generate_publisher_authority_id=lambda: PUBLISHER,
        generate_channel_id=lambda: CHANNEL,
        generate_channel_revision_id=lambda: CHANNEL_REVISION,
    ).bootstrap(ReleasePublicationBootstrapId("publication-bootstrap-251"),
                ReleasePublicationChannelDefinition("liquent", "package-index", "stable")) is not None
    projection = DatabaseCurrentReleaseAuthorityRegistryProjection(
        engine, verification_identity=ReleasePromotionVerifierId("verifier-251")
    )
    evidence = verify_release_promotion_with_projection(
        bundle_path=signed_candidate["bundle"], signature_path=signed_candidate["signature"],
        registry_projection=projection, key_id=KEY_ID,
        clock=lambda: datetime(2026, 8, 18, 14, tzinfo=timezone.utc),
    )
    evidence_path = tmp_path / "promotion.json"
    evidence_path.write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n")
    try:
        yield engine, signed_candidate, projection, evidence_path
    finally:
        engine.dispose()


def _store(engine, projection):
    return DatabaseAuthorizedReleasePublicationHandoff(
        engine, registry_projection=projection, clock=lambda: NOW
    )


def _accept(store, candidate, evidence, **changes):
    values = dict(handoff_id=HANDOFF, decision_id=DECISION,
                  publisher_authority_id=PUBLISHER, channel_id=CHANNEL,
                  expected_channel_revision=CHANNEL_REVISION,
                  bundle_path=str(candidate["bundle"]),
                  signature_path=str(candidate["signature"]),
                  promotion_evidence_path=str(evidence))
    values.update(changes)
    return store.accept_handoff(**values)


def test_current_promotion_publisher_and_channel_commit_ready_handoff(prepared):
    engine, candidate, projection, evidence = prepared
    assert _accept(_store(engine, projection), candidate, evidence) == AcceptedReleasePublicationHandoff(
        HANDOFF, DECISION, CHANNEL, CHANNEL_REVISION
    )
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT status,publisher_authority_id,channel_id FROM release_publication_handoffs"
        )).one()
        assert row == ("ready_for_publication", PUBLISHER.value.encode(), CHANNEL.value.encode())
        assert connection.scalar(text("SELECT count(*) FROM release_publication_receipts")) == 0


def test_exact_retry_uses_persisted_decision_without_projection(prepared):
    engine, candidate, projection, evidence = prepared
    first = _accept(_store(engine, projection), candidate, evidence)
    class Broken:
        def project(self): raise RuntimeError("must not project")
    assert _accept(_store(engine, Broken()), candidate, evidence) == first


def test_same_handoff_with_other_decision_is_conflict(prepared):
    engine, candidate, projection, evidence = prepared
    assert _accept(_store(engine, projection), candidate, evidence) is not None
    with pytest.raises(ReleasePublicationHandoffConflict):
        _accept(_store(engine, projection), candidate, evidence,
                decision_id=ReleasePublicationDecisionId("other"))


def test_stale_channel_or_inactive_publisher_is_neutral(prepared):
    engine, candidate, projection, evidence = prepared
    assert _accept(_store(engine, projection), candidate, evidence,
                   expected_channel_revision=ReleasePublicationChannelPolicyRevisionId("stale")) is None
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE release_publication_revision_publishers SET status='inactive'"
        ))
    assert _accept(_store(engine, projection), candidate, evidence) is None


def test_changed_promotion_evidence_is_neutral(prepared):
    engine, candidate, projection, evidence = prepared
    value = json.loads(evidence.read_text())
    value["registry_sha256"] = "0" * 64
    evidence.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    assert _accept(_store(engine, projection), candidate, evidence) is None
