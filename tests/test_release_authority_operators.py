import hashlib
import json
import subprocess
from pathlib import Path

from sqlalchemy import text

from liquent_platform.operators import release_key_activation as activation
from liquent_platform.operators import release_registry_bootstrap as bootstrap
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.database import build_engine
from liquent_platform.transport.release_key_activation_verification import (
    APPROVAL_NAMESPACE,
    PROOF_NAMESPACE,
)


def _private(path: Path, value: str | bytes) -> Path:
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(value)
    path.chmod(0o600)
    return path


def _json(path: Path, value: object) -> Path:
    return _private(
        path, json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    )


def _key(root: Path, name: str):
    private = root / name
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(private)],
        check=True, capture_output=True,
    )
    public_path = private.with_suffix(".pub")
    public = " ".join(public_path.read_text().split()[:2])
    fingerprint = subprocess.run(
        ["ssh-keygen", "-lf", str(public_path), "-E", "sha256"],
        check=True, capture_output=True, text=True,
    ).stdout.split()[1]
    return private, public, fingerprint


def _sign(root: Path, private: Path, namespace: str, value: bytes) -> bytes:
    payload = root / f"payload-{namespace}"
    payload.write_bytes(value)
    subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(private), "-n", namespace, str(payload)],
        check=True, capture_output=True,
    )
    signature = payload.with_suffix(payload.suffix + ".sig").read_bytes()
    payload.unlink()
    payload.with_suffix(payload.suffix + ".sig").unlink()
    return signature


def test_bootstrap_then_challenge_and_apply_with_fixed_reviewer_trust(
    tmp_path: Path, capsys
):
    engine = build_engine(f"sqlite:///{tmp_path / 'authority.db'}")
    upgrade_to_head(str(engine.url))
    engine.dispose()
    database_url = _private(
        tmp_path / "database-url", f"sqlite:///{tmp_path / 'authority.db'}\n"
    )
    signing_private, signing_public, signing_fingerprint = _key(
        tmp_path, "signing"
    )
    public_key = _private(tmp_path / "signing-public", signing_public + "\n")
    bootstrap_request = _json(
        tmp_path / "bootstrap.json", {"bootstrap_id": "bootstrap-lq280"}
    )
    assert bootstrap.main([
        "--database-url-file", str(database_url),
        "--request", str(bootstrap_request),
        "--public-key-file", str(public_key),
    ]) == 0
    bootstrapped = json.loads(capsys.readouterr().out)
    assert bootstrapped["outcome"] == "bootstrapped"
    assert bootstrap.main([
        "--database-url-file", str(database_url),
        "--request", str(bootstrap_request),
        "--public-key-file", str(public_key),
    ]) == 0
    assert json.loads(capsys.readouterr().out) == bootstrapped
    request = _json(tmp_path / "activation.json", {
        "actor_authority_id": bootstrapped["lifecycle_authority_id"],
        "change_id": "activation-lq280",
        "expected_revision": bootstrapped["registry_revision_id"],
        "key_id": bootstrapped["key_id"],
    })
    challenge_path = tmp_path / "challenge.json"
    assert activation.main([
        "challenge",
        "--database-url-file", str(database_url),
        "--request", str(request),
        "--output", str(challenge_path),
    ]) == 0
    assert capsys.readouterr().out == '{"outcome":"challenge_materialized"}\n'
    challenge = challenge_path.read_bytes()
    assert json.loads(challenge)["key_fingerprint"] == signing_fingerprint
    reviewer_private, reviewer_public, reviewer_fingerprint = _key(
        tmp_path, "reviewer"
    )
    trust = _json(tmp_path / "reviewers.json", {"reviewers": [{
        "fingerprint": reviewer_fingerprint,
        "public_key": reviewer_public,
        "reviewer_id": "reviewer-lq280",
    }]})
    proof = _private(
        tmp_path / "proof.sshsig",
        _sign(tmp_path, signing_private, PROOF_NAMESPACE, challenge),
    )
    approval = _private(
        tmp_path / "approval.sshsig",
        _sign(tmp_path, reviewer_private, APPROVAL_NAMESPACE, challenge),
    )
    result = activation.run_apply(
        database_url_file=database_url,
        request_file=request,
        proof_file=proof,
        approval_file=approval,
        reviewer_trust_path=trust,
    )
    assert result is not None
    assert result.reviewer_id.value == "reviewer-lq280"
    verify = build_engine(f"sqlite:///{tmp_path / 'authority.db'}")
    try:
        with verify.connect() as connection:
            assert connection.scalar(text(
                "SELECT status FROM release_registry_revision_keys"
                " WHERE revision_id=(SELECT revision_id"
                " FROM release_registry_current_set)"
            )) == "active"
    finally:
        verify.dispose()


def test_closed_requests_and_fixed_trust_are_not_cli_selectable(tmp_path: Path):
    request = _json(tmp_path / "bootstrap.json", {
        "bootstrap_id": "bootstrap-lq280", "allow": True,
    })
    try:
        bootstrap.load_request(request)
    except bootstrap.ReleaseRegistryBootstrapOperatorInputRejected:
        pass
    else:
        raise AssertionError("open bootstrap request accepted")
    help_text = activation._parser().format_help()
    assert "reviewer-trust" not in help_text
    assert str(activation.REVIEWER_TRUST_PATH) not in help_text
