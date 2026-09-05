from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_authority import (
    ActivatedReleaseSigningKey,
    ReleaseActivationReviewerId,
    ReleasePolicyRevisionId,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseRegistrySetRevisionId,
    ReleaseSignerAuthorityId,
    ReleaseSigningKeyId,
    ReleaseSigningPublicKey,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    ReleaseKeyActivationConflict,
    ReleaseKeyActivationUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.release_key_activation import (
    DatabaseReleaseKeyActivation,
)
from liquent_platform.persistence.release_registry_bootstrap import (
    DatabaseInitialReleaseRegistryBootstrap,
)


ACTOR = ReleaseRegistryLifecycleAuthorityId("lifecycle-242")
KEY = ReleaseSigningKeyId("key-242")
INITIAL = ReleaseRegistrySetRevisionId("revision-241")
RESULTING = ReleaseRegistrySetRevisionId("revision-242")
CHANGE = ReleaseRegistryLifecycleChangeId("activation-242")
REVIEWER = ReleaseActivationReviewerId("reviewer-242")
PUBLIC_KEY = ReleaseSigningPublicKey(
    "SHA256:" + "D" * 43,
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIActivationKey",
)


class ProofVerifier:
    def __init__(self, result=True, failure=None):
        self.result = result
        self.failure = failure
        self.calls = []

    def verify_proof(self, public_key, challenge, proof):
        self.calls.append((public_key, challenge, proof))
        if self.failure:
            raise self.failure
        return self.result


class ApprovalVerifier:
    def __init__(self, result=REVIEWER, failure=None):
        self.result = result
        self.failure = failure
        self.calls = []

    def verify_approval(self, challenge, approval):
        self.calls.append((challenge, approval))
        if self.failure:
            raise self.failure
        return self.result


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'activation.db'}")

    upgrade_to_head(str(database.url))
    bootstrap = DatabaseInitialReleaseRegistryBootstrap(
        database,
        generate_lifecycle_authority_id=lambda: ACTOR,
        generate_signer_authority_id=lambda: ReleaseSignerAuthorityId("signer-242"),
        generate_key_id=lambda: KEY,
        generate_registry_revision_id=lambda: INITIAL,
        generate_policy_revision_id=lambda: ReleasePolicyRevisionId("policy-242"),
    )
    assert bootstrap.bootstrap(
        ReleaseRegistryBootstrapId("bootstrap-242"), PUBLIC_KEY
    ) is not None
    try:
        yield database
    finally:
        database.dispose()


def _store(engine, proof=None, approval=None, revision=lambda: RESULTING):
    return DatabaseReleaseKeyActivation(
        engine,
        proof_verifier=proof or ProofVerifier(),
        approval_verifier=approval or ApprovalVerifier(),
        generate_revision_id=revision,
    )


def _activate(store, proof=b"proof", approval=b"approval", expected=INITIAL):
    return store.activate_key(CHANGE, ACTOR, KEY, expected, proof, approval)


def test_activation_copies_snapshot_and_only_activates_selected_key(engine: Engine):
    proof = ProofVerifier()
    approval = ApprovalVerifier()

    assert _activate(_store(engine, proof, approval)) == ActivatedReleaseSigningKey(
        CHANGE, KEY, RESULTING, REVIEWER
    )
    assert proof.calls[0][0] == PUBLIC_KEY.public_key
    assert b"liquent-release-key-possession-v1" in proof.calls[0][1]
    assert approval.calls[0][0] == proof.calls[0][1]
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT revision_id FROM release_registry_current_set"
        )).scalar_one() == RESULTING.value.encode()
        assert connection.execute(text(
            "SELECT status FROM release_registry_revision_keys "
            "WHERE revision_id=:revision"
        ), {"revision": RESULTING.value.encode()}).scalar_one() == "active"
        assert connection.execute(text(
            "SELECT status FROM release_registry_revision_keys "
            "WHERE revision_id=:revision"
        ), {"revision": INITIAL.value.encode()}).scalar_one() == "inactive"
        assert connection.execute(text(
            "SELECT intent,target_kind FROM release_registry_lifecycle_changes"
        )).one() == ("activate", "key")


@pytest.mark.parametrize("proof_result,approval_result", [
    (False, REVIEWER),
    (True, None),
    (True, ReleaseActivationReviewerId(ACTOR.value)),
])
def test_missing_proof_or_independent_approval_is_neutral(
    engine: Engine, proof_result, approval_result,
):
    proof = ProofVerifier(proof_result)
    approval = ApprovalVerifier(approval_result)
    generated = []

    assert _activate(_store(
        engine, proof, approval, lambda: generated.append(True)
    )) is None
    assert generated == []
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM release_key_activations")) == 0


def test_stale_revision_or_inactive_actor_fails_before_verifiers(engine: Engine):
    proof = ProofVerifier()
    approval = ApprovalVerifier()
    assert _activate(
        _store(engine, proof, approval),
        expected=ReleaseRegistrySetRevisionId("stale"),
    ) is None
    assert proof.calls == approval.calls == []


def test_exact_retry_survives_later_current_state_without_reverification(engine: Engine):
    first = _activate(_store(engine))
    proof = ProofVerifier(failure=RuntimeError("must not verify"))
    approval = ApprovalVerifier(failure=RuntimeError("must not verify"))

    assert _activate(_store(
        engine, proof, approval, lambda: (_ for _ in ()).throw(RuntimeError())
    )) == first
    assert proof.calls == approval.calls == []


def test_same_change_with_different_artifact_is_conflict(engine: Engine):
    assert _activate(_store(engine)) is not None
    with pytest.raises(ReleaseKeyActivationConflict) as raised:
        _activate(_store(engine), proof=b"other-proof")
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_verifier_and_generator_failures_roll_back_detail_free(engine: Engine):
    with pytest.raises(ReleaseKeyActivationUnavailable):
        _activate(_store(engine, ProofVerifier(failure=RuntimeError("secret"))))
    with pytest.raises(ReleaseKeyActivationUnavailable):
        _activate(_store(engine, revision=lambda: "wrong-type"))
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM release_key_activations")) == 0


def test_unmigrated_store_is_detail_free(tmp_path: Path):
    engine = build_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    try:
        with pytest.raises(ReleaseKeyActivationUnavailable) as raised:
            _activate(_store(engine))
        assert raised.value.args == ("release_key_activation_unavailable",)
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
    finally:
        engine.dispose()
