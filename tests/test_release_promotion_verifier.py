from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from test_operational_release_bundle import _build
from tools.release_promotion_verifier import (
    NAMESPACE,
    PromotionRejected,
    PromotionUnavailable,
    main,
    verify_release_promotion,
    verify_release_promotion_with_projection,
)


KEY_ID = "release-key-001"
AUTHORITY_ID = "release-authority-001"
DECISION_TIME = datetime(2026, 8, 17, 12, 30, tzinfo=timezone.utc)


class RegistryProjection:
    def __init__(self, value: bytes | None) -> None:
        self.value = value
        self.calls = 0

    def project(self) -> bytes | None:
        self.calls += 1
        return self.value


def _checksums(bundle: Path, destination: Path) -> None:
    with tarfile.open(bundle, "r:gz") as archive:
        matches = [
            member
            for member in archive.getmembers()
            if member.isfile() and member.name.endswith("/SHA256SUMS")
        ]
        assert len(matches) == 1
        extracted = archive.extractfile(matches[0])
        assert extracted is not None
        destination.write_bytes(extracted.read())


def _registry(
    path: Path,
    public_key: str,
    fingerprint: str,
    *,
    authority_status: str = "active",
    key_status: str = "active",
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "policy_revision": "release-policy:1",
                "policy_status": "active",
                "verification_identity": "independent-verifier-001",
                "authorities": [
                    {
                        "authority_id": AUTHORITY_ID,
                        "status": authority_status,
                        "keys": [
                            {
                                "key_id": KEY_ID,
                                "status": key_status,
                                "fingerprint": fingerprint,
                                "algorithm": "ssh-ed25519",
                                "namespaces": [NAMESPACE],
                                "public_key": public_key,
                            }
                        ],
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.fixture
def signed_candidate(tmp_path: Path) -> dict[str, Any]:
    bundle = _build(tmp_path / "candidate")
    private_key = tmp_path / "ephemeral-release-key"
    subprocess.run(
        [
            "ssh-keygen",
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "",
            "-f",
            str(private_key),
        ],
        check=True,
    )
    public_key = private_key.with_suffix(".pub").read_text(
        encoding="ascii"
    ).strip()
    public_key = " ".join(public_key.split()[:2])
    fingerprint = subprocess.run(
        ["ssh-keygen", "-lf", str(private_key.with_suffix(".pub")), "-E", "sha256"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()[1]
    checksums = tmp_path / "SHA256SUMS"
    _checksums(bundle, checksums)
    subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(private_key), "-n", NAMESPACE, str(checksums)],
        check=True,
        capture_output=True,
    )
    signature = bundle.with_name(bundle.name + ".sshsig")
    checksums.with_suffix(".sig").rename(signature)
    registry = tmp_path / "release-authorities.json"
    _registry(registry, public_key, fingerprint)
    return {
        "bundle": bundle,
        "signature": signature,
        "registry": registry,
        "public_key": public_key,
        "fingerprint": fingerprint,
    }


def _verify(candidate: dict[str, Any], **extra: Any) -> dict[str, object]:
    return verify_release_promotion(
        bundle_path=candidate["bundle"],
        signature_path=candidate["signature"],
        registry_path=candidate["registry"],
        key_id=KEY_ID,
        clock=lambda: DECISION_TIME,
        **extra,
    )


def test_verifies_signature_current_authority_and_emits_bound_evidence(
    signed_candidate: dict[str, Any],
) -> None:
    evidence = _verify(signed_candidate)

    assert evidence["integrity"] == "verified"
    assert evidence["signature"] == "verified"
    assert evidence["authority"] == "current"
    assert evidence["promotable"] is True
    assert evidence["signer_authority_id"] == AUTHORITY_ID
    assert evidence["key_id"] == KEY_ID
    assert evidence["key_fingerprint"] == signed_candidate["fingerprint"]
    assert evidence["namespace"] == NAMESPACE
    assert evidence["decided_at"] == "2026-08-17T12:30:00Z"
    assert len(evidence["bundle_sha256"]) == 64
    assert len(evidence["checksums_sha256"]) == 64
    assert len(evidence["signature_sha256"]) == 64
    assert len(evidence["registry_sha256"]) == 64


@pytest.mark.parametrize("authority_status,key_status", [
    ("inactive", "active"),
    ("active", "revoked"),
    ("active", "expired"),
])
def test_current_revocation_or_inactivity_blocks_later_decisions(
    signed_candidate: dict[str, Any], authority_status: str, key_status: str,
) -> None:
    assert _verify(signed_candidate)["promotable"] is True
    _registry(
        signed_candidate["registry"],
        signed_candidate["public_key"],
        signed_candidate["fingerprint"],
        authority_status=authority_status,
        key_status=key_status,
    )

    with pytest.raises(PromotionRejected, match="release promotion rejected"):
        _verify(signed_candidate)


def test_fingerprint_mismatch_and_signature_mutation_are_rejected(
    signed_candidate: dict[str, Any],
) -> None:
    _registry(
        signed_candidate["registry"],
        signed_candidate["public_key"],
        "SHA256:" + "A" * 43,
    )
    with pytest.raises(PromotionRejected):
        _verify(signed_candidate)

    _registry(
        signed_candidate["registry"],
        signed_candidate["public_key"],
        signed_candidate["fingerprint"],
    )
    signed_candidate["signature"].write_bytes(
        signed_candidate["signature"].read_bytes() + b"x"
    )
    with pytest.raises(PromotionRejected):
        _verify(signed_candidate)


def test_wrong_key_reference_and_signature_filename_are_rejected(
    signed_candidate: dict[str, Any],
) -> None:
    with pytest.raises(PromotionRejected):
        verify_release_promotion(
            bundle_path=signed_candidate["bundle"],
            signature_path=signed_candidate["signature"],
            registry_path=signed_candidate["registry"],
            key_id="caller-asserted-key",
            clock=lambda: DECISION_TIME,
        )
    renamed = signed_candidate["signature"].with_name("unbound.sshsig")
    signed_candidate["signature"].rename(renamed)
    with pytest.raises(PromotionRejected):
        verify_release_promotion(
            bundle_path=signed_candidate["bundle"],
            signature_path=renamed,
            registry_path=signed_candidate["registry"],
            key_id=KEY_ID,
            clock=lambda: DECISION_TIME,
        )


def test_corrupt_registry_and_missing_crypto_provider_are_unavailable(
    signed_candidate: dict[str, Any],
) -> None:
    signed_candidate["registry"].write_text("not json", encoding="utf-8")
    with pytest.raises(PromotionUnavailable):
        _verify(signed_candidate)

    _registry(
        signed_candidate["registry"],
        signed_candidate["public_key"],
        signed_candidate["fingerprint"],
    )
    with pytest.raises(PromotionUnavailable):
        _verify(signed_candidate, ssh_keygen="missing-ssh-keygen")


def test_cli_keeps_rejection_detail_free(
    signed_candidate: dict[str, Any], capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([
        "--bundle", str(signed_candidate["bundle"]),
        "--signature", str(signed_candidate["signature"]),
        "--registry", str(signed_candidate["registry"]),
        "--key-id", "unknown-key",
    ]) == 2
    assert json.loads(capsys.readouterr().out) == {
        "error": "release_promotion_rejected"
    }


def test_projection_composition_uses_exactly_one_current_snapshot(
    signed_candidate: dict[str, Any],
) -> None:
    value = signed_candidate["registry"].read_bytes()
    projection = RegistryProjection(value)

    evidence = verify_release_promotion_with_projection(
        bundle_path=signed_candidate["bundle"],
        signature_path=signed_candidate["signature"],
        registry_projection=projection,
        key_id=KEY_ID,
        clock=lambda: DECISION_TIME,
    )

    assert projection.calls == 1
    assert evidence["registry_sha256"] == hashlib.sha256(value).hexdigest()
    assert evidence["promotable"] is True


def test_projection_absence_is_neutral_rejection(
    signed_candidate: dict[str, Any],
) -> None:
    projection = RegistryProjection(None)

    with pytest.raises(PromotionRejected) as raised:
        verify_release_promotion_with_projection(
            bundle_path=signed_candidate["bundle"],
            signature_path=signed_candidate["signature"],
            registry_projection=projection,
            key_id=KEY_ID,
        )

    assert str(raised.value) == "release promotion rejected"
    assert projection.calls == 1


@pytest.mark.parametrize("value", [b"", bytearray(b"registry")])
def test_invalid_projection_result_is_detail_free_unavailability(
    signed_candidate: dict[str, Any], value: object,
) -> None:
    projection = RegistryProjection(value)  # type: ignore[arg-type]

    with pytest.raises(PromotionUnavailable) as raised:
        verify_release_promotion_with_projection(
            bundle_path=signed_candidate["bundle"],
            signature_path=signed_candidate["signature"],
            registry_projection=projection,
            key_id=KEY_ID,
        )

    assert str(raised.value) == "release promotion verification unavailable"
    assert projection.calls == 1


def test_projection_failure_is_detail_free_unavailability(
    signed_candidate: dict[str, Any],
) -> None:
    class BrokenProjection:
        def project(self) -> bytes | None:
            raise RuntimeError("database details")

    with pytest.raises(PromotionUnavailable) as raised:
        verify_release_promotion_with_projection(
            bundle_path=signed_candidate["bundle"],
            signature_path=signed_candidate["signature"],
            registry_projection=BrokenProjection(),
            key_id=KEY_ID,
        )

    assert str(raised.value) == "release promotion verification unavailable"
