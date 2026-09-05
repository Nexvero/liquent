import hashlib
import json
from pathlib import Path

import pytest

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
from liquent_platform.operators.release_promotion import (
    ReleasePromotionOperatorInputRejected,
    ReleasePromotionOperatorUnavailable,
    ReleasePromotionRequest,
    load_request,
    materialize_evidence,
    verify_promotion,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.release_key_activation import DatabaseReleaseKeyActivation
from liquent_platform.persistence.release_registry_bootstrap import (
    DatabaseInitialReleaseRegistryBootstrap,
)
from liquent_platform.persistence.release_registry_projection import (
    DatabaseCurrentReleaseAuthorityRegistryProjection,
)
from test_release_promotion_verifier import (
    AUTHORITY_ID,
    KEY_ID,
    RegistryProjection,
    signed_candidate,
)


class Proof:
    def verify_proof(self, public_key, challenge, proof):
        return True


class Approval:
    def verify_approval(self, challenge, approval):
        return ReleaseActivationReviewerId("reviewer-247")


def _private(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")
    path.chmod(0o600)


def _request(candidate: dict[str, object], tmp_path: Path) -> ReleasePromotionRequest:
    return ReleasePromotionRequest(
        candidate["bundle"],
        candidate["signature"],
        KEY_ID,
        tmp_path / "promotion-evidence.json",
    )


def test_closed_private_request_has_no_registry_authority_or_allow(tmp_path: Path):
    request_path = tmp_path / "request.json"
    bundle = tmp_path / "candidate.tar.gz"
    value = {
        "bundle_path": str(bundle),
        "signature_path": str(bundle) + ".sshsig",
        "key_id": KEY_ID,
        "evidence_path": str(tmp_path / "promotion.json"),
    }
    _private(request_path, value)

    assert load_request(request_path) == ReleasePromotionRequest(
        bundle, Path(str(bundle) + ".sshsig"), KEY_ID,
        tmp_path / "promotion.json",
    )

    value["registry_path"] = "/caller/trust.json"
    _private(request_path, value)
    with pytest.raises(ReleasePromotionOperatorInputRejected):
        load_request(request_path)


def test_verification_uses_one_projected_snapshot_and_canonical_evidence(
    signed_candidate: dict[str, object], tmp_path: Path,
):
    registry = signed_candidate["registry"].read_bytes()
    projection = RegistryProjection(registry)

    evidence = verify_promotion(_request(signed_candidate, tmp_path), projection)

    parsed = json.loads(evidence)
    assert projection.calls == 1
    assert evidence == (
        json.dumps(parsed, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")
    assert parsed["registry_sha256"] == hashlib.sha256(registry).hexdigest()
    assert parsed["promotable"] is True


def test_operator_composes_real_persistent_current_registry(
    signed_candidate: dict[str, object], tmp_path: Path,
):
    engine = build_engine(f"sqlite:///{tmp_path / 'promotion.db'}")
    upgrade_to_head(str(engine.url))
    initial = ReleaseRegistrySetRevisionId("revision-246")
    active = ReleaseRegistrySetRevisionId("revision-247")
    lifecycle = ReleaseRegistryLifecycleAuthorityId("lifecycle-247")
    key = ReleaseSigningKeyId(KEY_ID)
    bootstrap = DatabaseInitialReleaseRegistryBootstrap(
        engine,
        generate_lifecycle_authority_id=lambda: lifecycle,
        generate_signer_authority_id=lambda: ReleaseSignerAuthorityId(AUTHORITY_ID),
        generate_key_id=lambda: key,
        generate_registry_revision_id=lambda: initial,
        generate_policy_revision_id=lambda: ReleasePolicyRevisionId("policy-247"),
    ).bootstrap(
        ReleaseRegistryBootstrapId("bootstrap-247"),
        ReleaseSigningPublicKey(
            signed_candidate["fingerprint"], signed_candidate["public_key"]
        ),
    )
    assert bootstrap is not None
    assert DatabaseReleaseKeyActivation(
        engine, proof_verifier=Proof(), approval_verifier=Approval(),
        generate_revision_id=lambda: active,
    ).activate_key(
        ReleaseRegistryLifecycleChangeId("activation-247"), lifecycle, key,
        initial, b"proof", b"approval",
    ) is not None
    projection = DatabaseCurrentReleaseAuthorityRegistryProjection(
        engine, verification_identity=ReleasePromotionVerifierId("verifier-247")
    )
    try:
        parsed = json.loads(verify_promotion(
            _request(signed_candidate, tmp_path), projection
        ))
    finally:
        engine.dispose()
    assert parsed["verification_identity"] == "verifier-247"
    assert parsed["key_id"] == KEY_ID


def test_evidence_is_private_exclusive_and_never_overwritten(tmp_path: Path):
    tmp_path.chmod(0o700)
    path = tmp_path / "promotion.json"
    evidence = b'{"promotable":true}\n'

    result = materialize_evidence(path, evidence)

    assert result.evidence_path == path
    assert path.read_bytes() == evidence
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ReleasePromotionOperatorUnavailable):
        materialize_evidence(path, evidence)
    assert path.read_bytes() == evidence


def test_symlink_and_insecure_parent_are_fail_closed(tmp_path: Path):
    target = tmp_path / "target"
    target.write_bytes(b"foreign")
    link = tmp_path / "promotion.json"
    link.symlink_to(target)
    with pytest.raises(ReleasePromotionOperatorUnavailable):
        materialize_evidence(link, b"evidence")
    assert target.read_bytes() == b"foreign"

    link.unlink()
    tmp_path.chmod(0o755)
    with pytest.raises(ReleasePromotionOperatorUnavailable):
        materialize_evidence(link, b"evidence")
