import json
import os
from pathlib import Path

import pytest

from liquent_platform.identity.release_authority import (
    ReleaseRegistrySetRevisionId,
    ReleaseSigningDecisionId,
    ReleaseSigningKeyId,
    SignedReleaseCandidate,
)
from liquent_platform.operators.release_signing import (
    OpenSshReleaseSignatureVerifier,
    OpenSshSigningKeyProvider,
    ReleaseSigningOperatorInputRejected,
    ReleaseSigningOperatorUnavailable,
    ReleaseSigningRequest,
    load_request,
    materialize_outputs,
)
from liquent_platform.persistence.release_signing import NAMESPACE


DECISION = ReleaseSigningDecisionId("decision-246")
RESULT = SignedReleaseCandidate(DECISION, b"signature-bytes", b"evidence-bytes")


def _private(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")
    path.chmod(0o600)


def _request(tmp_path: Path) -> ReleaseSigningRequest:
    bundle = tmp_path / "candidate.tar.gz"
    return ReleaseSigningRequest(
        DECISION,
        ReleaseSigningKeyId("key-246"),
        ReleaseRegistrySetRevisionId("revision-246"),
        bundle,
        tmp_path / "candidate.tar.gz.sshsig",
        tmp_path / "candidate.signing.json",
    )


def test_private_closed_request_is_loaded_without_authority_or_allow(tmp_path: Path):
    request_path = tmp_path / "request.json"
    request = _request(tmp_path)
    _private(request_path, {
        "decision_id": request.decision_id.value,
        "key_id": request.key_id.value,
        "expected_revision": request.expected_revision.value,
        "bundle_path": str(request.bundle_path),
        "signature_path": str(request.signature_path),
        "evidence_path": str(request.evidence_path),
    })

    assert load_request(request_path) == request

    value = json.loads(request_path.read_text())
    value["allow"] = True
    _private(request_path, value)
    with pytest.raises(ReleaseSigningOperatorInputRejected):
        load_request(request_path)


def test_outputs_are_exclusive_private_and_exact_retry_is_recovered(tmp_path: Path):
    tmp_path.chmod(0o700)
    request = _request(tmp_path)

    first = materialize_outputs(request, RESULT)

    assert first.recovered is False
    assert request.signature_path.read_bytes() == RESULT.signature
    assert request.evidence_path.read_bytes() == RESULT.evidence
    assert request.signature_path.stat().st_mode & 0o777 == 0o600
    assert request.evidence_path.stat().st_mode & 0o777 == 0o600
    assert materialize_outputs(request, RESULT).recovered is True


@pytest.mark.parametrize("existing", ["signature", "evidence", "different"])
def test_partial_or_different_outputs_are_never_overwritten(
    tmp_path: Path, existing: str,
):
    tmp_path.chmod(0o700)
    request = _request(tmp_path)
    path = request.signature_path if existing != "evidence" else request.evidence_path
    value = b"different" if existing == "different" else (
        RESULT.signature if existing == "signature" else RESULT.evidence
    )
    path.write_bytes(value)
    path.chmod(0o600)

    with pytest.raises(ReleaseSigningOperatorUnavailable):
        materialize_outputs(request, RESULT)

    assert path.read_bytes() == value
    other = request.evidence_path if path == request.signature_path else request.signature_path
    assert not other.exists()


def test_insecure_output_parent_is_rejected(tmp_path: Path):
    tmp_path.chmod(0o755)
    with pytest.raises(ReleaseSigningOperatorUnavailable):
        materialize_outputs(_request(tmp_path), RESULT)


def test_openssh_provider_and_independent_verifier_use_exact_payload(tmp_path: Path):
    private_key = tmp_path / "release-key"
    os.chmod(tmp_path, 0o700)
    import subprocess
    subprocess.run([
        "ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "",
        "-f", str(private_key),
    ], check=True)
    private_key.chmod(0o600)
    public_key = " ".join(
        private_key.with_suffix(".pub").read_text(encoding="ascii").split()[:2]
    )
    payload = b"abc  artifact.whl\n"
    provider = OpenSshSigningKeyProvider(private_key)

    signature = provider.sign(payload, NAMESPACE)

    assert provider.fingerprint().startswith("SHA256:")
    assert signature.startswith(b"-----BEGIN SSH SIGNATURE-----\n")
    assert OpenSshReleaseSignatureVerifier().verify(
        public_key, "signer-246", payload, signature
    ) is True
    assert OpenSshReleaseSignatureVerifier().verify(
        public_key, "signer-246", payload + b"changed", signature
    ) is False
