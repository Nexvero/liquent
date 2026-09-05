from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_authority import (
    ReleaseActivationReviewerId,
    ReleasePolicyRevisionId,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseRegistrySetRevisionId,
    ReleaseSignerAuthorityId,
    ReleaseSigningDecisionId,
    ReleaseSigningExecutorId,
    ReleaseSigningKeyId,
    ReleaseSigningPublicKey,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    ReleaseSigningConflict,
    ReleaseSigningUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.release_key_activation import DatabaseReleaseKeyActivation
from liquent_platform.persistence.release_registry_bootstrap import (
    DatabaseInitialReleaseRegistryBootstrap,
)
from liquent_platform.persistence.release_signing import DatabaseReleaseSigning, NAMESPACE
from test_operational_release_bundle import _build


KEY = ReleaseSigningKeyId("key-245")
INITIAL = ReleaseRegistrySetRevisionId("revision-244")
ACTIVE = ReleaseRegistrySetRevisionId("revision-245")
DECISION = ReleaseSigningDecisionId("signing-245")
FINGERPRINT = "SHA256:" + "S" * 43
PUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAISigningKey"
NOW = datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc)


class Proof:
    def verify_proof(self, public_key, challenge, proof):
        return True


class Approval:
    def verify_approval(self, challenge, approval):
        return ReleaseActivationReviewerId("reviewer-245")


class Provider:
    def __init__(self, fingerprint=FINGERPRINT, failure=None):
        self.value = fingerprint
        self.failure = failure
        self.calls = []

    def fingerprint(self):
        return self.value

    def sign(self, payload, namespace):
        self.calls.append((payload, namespace))
        if self.failure:
            raise self.failure
        return b"canonical-sshsig"


class Verifier:
    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def verify(self, public_key, authority_id, payload, signature):
        self.calls.append((public_key, authority_id, payload, signature))
        return self.result


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'signing.db'}")

    upgrade_to_head(str(database.url))
    bootstrap = DatabaseInitialReleaseRegistryBootstrap(
        database,
        generate_lifecycle_authority_id=lambda: ReleaseRegistryLifecycleAuthorityId("lifecycle-245"),
        generate_signer_authority_id=lambda: ReleaseSignerAuthorityId("signer-245"),
        generate_key_id=lambda: KEY,
        generate_registry_revision_id=lambda: INITIAL,
        generate_policy_revision_id=lambda: ReleasePolicyRevisionId("policy-245"),
    ).bootstrap(
        ReleaseRegistryBootstrapId("bootstrap-245"),
        ReleaseSigningPublicKey(FINGERPRINT, PUBLIC_KEY),
    )
    assert bootstrap is not None
    activated = DatabaseReleaseKeyActivation(
        database,
        proof_verifier=Proof(),
        approval_verifier=Approval(),
        generate_revision_id=lambda: ACTIVE,
    ).activate_key(
        ReleaseRegistryLifecycleChangeId("activation-245"),
        bootstrap.lifecycle_authority_id,
        KEY,
        INITIAL,
        b"proof",
        b"approval",
    )
    assert activated is not None
    try:
        yield database
    finally:
        database.dispose()


def _store(engine, provider=None, verifier=None):
    return DatabaseReleaseSigning(
        engine,
        executor_id=ReleaseSigningExecutorId("executor-245"),
        key_provider=provider or Provider(),
        signature_verifier=verifier or Verifier(),
        clock=lambda: NOW,
    )


def test_current_authority_signs_verifies_and_persists_exact_evidence(
    engine: Engine, tmp_path: Path,
) -> None:
    bundle = _build(tmp_path / "candidate")
    provider = Provider()
    verifier = Verifier()

    result = _store(engine, provider, verifier).sign_candidate(
        DECISION, KEY, ACTIVE, str(bundle)
    )

    assert result is not None
    assert result.signature == b"canonical-sshsig"
    assert provider.calls[0][1] == NAMESPACE
    assert verifier.calls == [(PUBLIC_KEY, "signer-245", provider.calls[0][0], result.signature)]
    evidence = json.loads(result.evidence)
    assert evidence["decision_id"] == DECISION.value
    assert evidence["registry_revision_id"] == ACTIVE.value
    assert evidence["executor_identity"] == "executor-245"
    assert evidence["outcome"] == "signed"
    with engine.connect() as connection:
        row = connection.execute(text("SELECT signature,evidence FROM release_signing_decisions")).one()
    assert row == (result.signature, result.evidence)


def test_stale_revision_and_provider_fingerprint_fail_before_signing(
    engine: Engine, tmp_path: Path,
) -> None:
    bundle = _build(tmp_path / "candidate")
    provider = Provider()
    assert _store(engine, provider).sign_candidate(
        DECISION, KEY, ReleaseRegistrySetRevisionId("stale"), str(bundle)
    ) is None
    assert provider.calls == []
    wrong = Provider("SHA256:" + "W" * 43)
    assert _store(engine, wrong).sign_candidate(DECISION, KEY, ACTIVE, str(bundle)) is None
    assert wrong.calls == []


def test_exact_retry_returns_persisted_bytes_without_provider(
    engine: Engine, tmp_path: Path,
) -> None:
    bundle = _build(tmp_path / "candidate")
    first = _store(engine).sign_candidate(DECISION, KEY, ACTIVE, str(bundle))
    broken = Provider(failure=RuntimeError("private provider detail"))
    second = _store(engine, broken).sign_candidate(DECISION, KEY, ACTIVE, str(bundle))
    assert second == first
    assert broken.calls == []


def test_decision_id_reuse_with_different_input_is_conflict(
    engine: Engine, tmp_path: Path,
) -> None:
    bundle = _build(tmp_path / "candidate")
    assert _store(engine).sign_candidate(DECISION, KEY, ACTIVE, str(bundle)) is not None
    with pytest.raises(ReleaseSigningConflict):
        _store(engine).sign_candidate(
            DECISION, ReleaseSigningKeyId("other-key"), ACTIVE, str(bundle)
        )


@pytest.mark.parametrize("failure", [RuntimeError("provider secret"), None])
def test_provider_or_verification_failure_rolls_back_detail_free(
    engine: Engine, tmp_path: Path, failure,
) -> None:
    bundle = _build(tmp_path / "candidate")
    provider = Provider(failure=failure)
    verifier = Verifier(result=failure is not None)
    with pytest.raises(ReleaseSigningUnavailable) as raised:
        _store(engine, provider, verifier).sign_candidate(DECISION, KEY, ACTIVE, str(bundle))
    assert raised.value.args == ("release_signing_unavailable",)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM release_signing_decisions")) == 0
