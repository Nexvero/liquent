import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from liquent_platform.identity.release_authority import (
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
from liquent_platform.transport.release_key_activation_verification import (
    APPROVAL_NAMESPACE,
    PROOF_NAMESPACE,
    OpenSshReleaseKeyActivationApprovalVerifier,
    OpenSshReleaseKeyProofVerifier,
    ReleaseActivationReviewerTrust,
    ReleaseKeyActivationVerificationUnavailable,
    compose_release_key_activation_verification,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.release_key_activation import (
    DatabaseReleaseKeyActivation,
)
from liquent_platform.persistence.release_registry_bootstrap import (
    DatabaseInitialReleaseRegistryBootstrap,
)


def _key(root: Path, name: str) -> tuple[Path, str, str]:
    private = root / name
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(private)],
        check=True,
        capture_output=True,
    )
    public = " ".join(private.with_suffix(".pub").read_text().split()[:2])
    fingerprint = subprocess.run(
        ["ssh-keygen", "-lf", str(private.with_suffix(".pub")), "-E", "sha256"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()[1]
    return private, public, fingerprint


def _sign(root: Path, private: Path, namespace: str, value: bytes) -> bytes:
    payload = root / f"payload-{namespace}"
    payload.write_bytes(value)
    subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(private), "-n", namespace, str(payload)],
        check=True,
        capture_output=True,
    )
    signature = payload.with_suffix(payload.suffix + ".sig").read_bytes()
    payload.unlink()
    payload.with_suffix(payload.suffix + ".sig").unlink()
    return signature


def test_proof_is_exact_detached_sshsig_over_bound_challenge(tmp_path: Path):
    private, public, _ = _key(tmp_path, "possession")
    challenge = b'{"namespace":"liquent-release-key-possession-v1"}\n'
    proof = _sign(tmp_path, private, PROOF_NAMESPACE, challenge)
    verifier = OpenSshReleaseKeyProofVerifier()
    assert verifier.verify_proof(public, challenge, proof) is True
    assert verifier.verify_proof(public, challenge + b"changed", proof) is False
    assert verifier.verify_proof(public, challenge, b"not-sshsig") is False
    assert repr(verifier) == "OpenSshReleaseKeyProofVerifier()"


def test_approval_identity_comes_only_from_fixed_matching_trust(tmp_path: Path):
    reviewer_private, reviewer_public, fingerprint = _key(tmp_path, "reviewer")
    other_private, other_public, other_fingerprint = _key(tmp_path, "other")
    challenge = b"canonical-activation-challenge\n"
    approval = _sign(tmp_path, reviewer_private, APPROVAL_NAMESPACE, challenge)
    reviewers = (
        ReleaseActivationReviewerTrust(
            ReleaseActivationReviewerId("reviewer-lq279"),
            reviewer_public,
            fingerprint,
        ),
        ReleaseActivationReviewerTrust(
            ReleaseActivationReviewerId("other-lq279"),
            other_public,
            other_fingerprint,
        ),
    )
    verifier = OpenSshReleaseKeyActivationApprovalVerifier(reviewers)
    assert verifier.verify_approval(challenge, approval) == (
        ReleaseActivationReviewerId("reviewer-lq279")
    )
    unknown = _sign(tmp_path, other_private, PROOF_NAMESPACE, challenge)
    assert verifier.verify_approval(challenge, unknown) is None
    assert repr(verifier) == "OpenSshReleaseKeyActivationApprovalVerifier()"


def test_reviewer_fingerprint_mismatch_and_duplicate_trust_fail_closed(
    tmp_path: Path,
):
    private, public, fingerprint = _key(tmp_path, "reviewer")
    challenge = b"challenge\n"
    approval = _sign(tmp_path, private, APPROVAL_NAMESPACE, challenge)
    wrong = ReleaseActivationReviewerTrust(
        ReleaseActivationReviewerId("reviewer-lq279"),
        public,
        "SHA256:" + "A" * 43,
    )
    assert OpenSshReleaseKeyActivationApprovalVerifier(
        (wrong,)
    ).verify_approval(challenge, approval) is None
    trusted = ReleaseActivationReviewerTrust(
        ReleaseActivationReviewerId("reviewer-lq279"), public, fingerprint
    )
    with pytest.raises(ValueError):
        OpenSshReleaseKeyActivationApprovalVerifier((trusted, trusted))


def test_composition_is_io_free_and_missing_crypto_is_detail_free(tmp_path: Path):
    _private, public, fingerprint = _key(tmp_path, "reviewer")
    trust = ReleaseActivationReviewerTrust(
        ReleaseActivationReviewerId("reviewer-lq279"), public, fingerprint
    )
    composition = compose_release_key_activation_verification(
        reviewers=(trust,), ssh_keygen="missing-liquent-ssh-keygen"
    )
    assert repr(composition) == "ReleaseKeyActivationVerificationComposition()"
    with pytest.raises(ReleaseKeyActivationVerificationUnavailable) as raised:
        composition.approval_verifier.verify_approval(
            b"challenge", b"-----BEGIN SSH SIGNATURE-----\nAA==\n-----END SSH SIGNATURE-----\n"
        )
    assert raised.value.args == ("release_key_activation_verification_unavailable",)
    assert raised.value.__cause__ is None


def test_fixed_verifiers_activate_through_persistent_store(tmp_path: Path):
    key_private, key_public, key_fingerprint = _key(tmp_path, "signing-key")
    reviewer_private, reviewer_public, reviewer_fingerprint = _key(
        tmp_path, "reviewer-key"
    )
    actor = ReleaseRegistryLifecycleAuthorityId("lifecycle-lq279")
    key_id = ReleaseSigningKeyId("key-lq279")
    initial = ReleaseRegistrySetRevisionId("revision-lq279-initial")
    change = ReleaseRegistryLifecycleChangeId("change-lq279")
    values = {
        "actor_authority_id": actor.value,
        "change_id": change.value,
        "expected_revision_id": initial.value,
        "key_fingerprint": key_fingerprint,
        "key_id": key_id.value,
        "public_key_sha256": hashlib.sha256(key_public.encode("ascii")).hexdigest(),
    }
    challenge = (
        json.dumps(
            {
                "schema_version": 1,
                "namespace": PROOF_NAMESPACE,
                **values,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("ascii")
    proof = _sign(tmp_path, key_private, PROOF_NAMESPACE, challenge)
    approval = _sign(tmp_path, reviewer_private, APPROVAL_NAMESPACE, challenge)
    trust = ReleaseActivationReviewerTrust(
        ReleaseActivationReviewerId("reviewer-lq279"),
        reviewer_public,
        reviewer_fingerprint,
    )
    verification = compose_release_key_activation_verification(reviewers=(trust,))
    database = build_engine(f"sqlite:///{tmp_path / 'activation.db'}")
    upgrade_to_head(str(database.url))
    try:
        bootstrap = DatabaseInitialReleaseRegistryBootstrap(
            database,
            generate_lifecycle_authority_id=lambda: actor,
            generate_signer_authority_id=lambda: ReleaseSignerAuthorityId(
                "signer-lq279"
            ),
            generate_key_id=lambda: key_id,
            generate_registry_revision_id=lambda: initial,
            generate_policy_revision_id=lambda: ReleasePolicyRevisionId(
                "policy-lq279"
            ),
        ).bootstrap(
            ReleaseRegistryBootstrapId("bootstrap-lq279"),
            ReleaseSigningPublicKey(key_fingerprint, key_public),
        )
        assert bootstrap is not None
        result = DatabaseReleaseKeyActivation(
            database,
            proof_verifier=verification.proof_verifier,
            approval_verifier=verification.approval_verifier,
            generate_revision_id=lambda: ReleaseRegistrySetRevisionId(
                "revision-lq279-active"
            ),
        ).activate_key(change, actor, key_id, initial, proof, approval)
        assert result is not None
        assert result.reviewer_id == ReleaseActivationReviewerId("reviewer-lq279")
    finally:
        database.dispose()
