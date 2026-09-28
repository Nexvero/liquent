#!/usr/bin/env python3
"""Verify one LQ-237 detached release signature without publishing it."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, NoReturn

from liquent_platform.identity.ports import (
    CurrentReleaseAuthorityRegistryProjection,
)
from liquent_platform.persistence.identity_errors import (
    ReleaseRegistryProjectionUnavailable,
)
from tools.operational_release_bundle import BundleRejected, verify_bundle


NAMESPACE = "liquent-operations-release-v1"
ID_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?")
FINGERPRINT_RE = re.compile(r"SHA256:[A-Za-z0-9+/]{43}")
POLICY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
SSHSIG_RE = re.compile(
    rb"-----BEGIN SSH SIGNATURE-----\n"
    rb"(?:[A-Za-z0-9+/=]+\n)+"
    rb"-----END SSH SIGNATURE-----\n"
)
REGISTRY_KEYS = {
    "schema_version",
    "policy_revision",
    "policy_status",
    "verification_identity",
    "authorities",
}
AUTHORITY_KEYS = {"authority_id", "status", "keys"}
KEY_KEYS = {
    "key_id",
    "status",
    "fingerprint",
    "algorithm",
    "namespaces",
    "public_key",
}


class PromotionRejected(Exception):
    """Report one detail-limited non-authorizing promotion decision."""


class PromotionUnavailable(Exception):
    """Report detail-limited technical verification unavailability."""


def _reject() -> NoReturn:
    raise PromotionRejected("release promotion rejected")


def _unavailable() -> NoReturn:
    raise PromotionUnavailable("release promotion verification unavailable")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_regular(path: Path, *, unavailable: bool = False) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            if unavailable:
                _unavailable()
            _reject()
        return path.read_bytes()
    except (PromotionRejected, PromotionUnavailable):
        raise
    except OSError:
        _unavailable()


def _registry(value: bytes) -> dict[str, Any]:
    try:
        registry = json.loads(value)
    except (UnicodeError, json.JSONDecodeError):
        _unavailable()
    if not isinstance(registry, dict) or set(registry) != REGISTRY_KEYS:
        _unavailable()
    if registry.get("schema_version") != 1:
        _unavailable()
    if registry.get("policy_status") != "active":
        _reject()
    policy = registry.get("policy_revision")
    verifier = registry.get("verification_identity")
    if (
        not isinstance(policy, str)
        or not POLICY_RE.fullmatch(policy)
        or not isinstance(verifier, str)
        or not ID_RE.fullmatch(verifier)
    ):
        _unavailable()
    authorities = registry.get("authorities")
    if not isinstance(authorities, list):
        _unavailable()
    return registry


def _current_key(
    registry: dict[str, Any], key_id: str
) -> tuple[str, dict[str, Any]]:
    if not ID_RE.fullmatch(key_id):
        _reject()
    matches: list[tuple[str, dict[str, Any]]] = []
    authority_ids: set[str] = set()
    seen_keys: set[str] = set()
    seen_fingerprints: set[str] = set()
    for authority in registry["authorities"]:
        if not isinstance(authority, dict) or set(authority) != AUTHORITY_KEYS:
            _unavailable()
        authority_id = authority.get("authority_id")
        authority_status = authority.get("status")
        keys = authority.get("keys")
        if (
            not isinstance(authority_id, str)
            or not ID_RE.fullmatch(authority_id)
            or authority_id in authority_ids
            or authority_status not in {"active", "inactive"}
            or not isinstance(keys, list)
        ):
            _unavailable()
        authority_ids.add(authority_id)
        for key in keys:
            if not isinstance(key, dict) or set(key) != KEY_KEYS:
                _unavailable()
            item_id = key.get("key_id")
            key_status = key.get("status")
            fingerprint = key.get("fingerprint")
            public_key = key.get("public_key")
            if (
                not isinstance(item_id, str)
                or not ID_RE.fullmatch(item_id)
                or item_id in seen_keys
                or key_status not in {"active", "inactive", "expired", "revoked"}
                or key.get("algorithm") != "ssh-ed25519"
                or key.get("namespaces") != [NAMESPACE]
                or not isinstance(fingerprint, str)
                or not FINGERPRINT_RE.fullmatch(fingerprint)
                or fingerprint in seen_fingerprints
                or not isinstance(public_key, str)
                or "\n" in public_key
                or len(public_key.split()) != 2
                or not public_key.startswith("ssh-ed25519 ")
            ):
                _unavailable()
            seen_keys.add(item_id)
            seen_fingerprints.add(fingerprint)
            if item_id == key_id:
                matches.append(
                    (authority_id, {**key, "authority_status": authority_status})
                )
    if len(matches) != 1:
        _reject()
    authority_id, key = matches[0]
    if key["authority_status"] != "active" or key.get("status") != "active":
        _reject()
    return authority_id, key


def _bundle_snapshot(value: bytes, filename: str) -> tuple[dict[str, object], bytes]:
    try:
        with tempfile.TemporaryDirectory(prefix="liquent-promotion-") as directory:
            snapshot = Path(directory) / filename
            snapshot.write_bytes(value)
            result = verify_bundle(snapshot)
    except BundleRejected:
        _reject()
    except OSError:
        _unavailable()

    checksums: list[bytes] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(value), mode="r:gz") as archive:
            for member in archive.getmembers():
                if member.isfile() and member.name.endswith("/SHA256SUMS"):
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        _reject()
                    checksums.append(extracted.read())
    except (OSError, tarfile.TarError):
        _reject()
    if len(checksums) != 1:
        _reject()
    return result, checksums[0]


def _fingerprint_and_verify(
    *, public_key: str, expected_fingerprint: str, authority_id: str,
    signature: bytes, checksums: bytes, ssh_keygen: str,
) -> None:
    try:
        with tempfile.TemporaryDirectory(prefix="liquent-sshsig-") as directory:
            root = Path(directory)
            public_path = root / "release-key.pub"
            allowed_path = root / "allowed_signers"
            signature_path = root / "candidate.sshsig"
            public_path.write_text(public_key + "\n", encoding="ascii")
            allowed_path.write_text(
                f'{authority_id} namespaces="{NAMESPACE}" {public_key}\n',
                encoding="ascii",
            )
            signature_path.write_bytes(signature)
            os.chmod(public_path, 0o600)
            os.chmod(allowed_path, 0o600)
            os.chmod(signature_path, 0o600)
            fingerprint = subprocess.run(
                [ssh_keygen, "-lf", str(public_path), "-E", "sha256"],
                check=True, capture_output=True, text=True,
            ).stdout.split()[1]
            if fingerprint != expected_fingerprint:
                _reject()
            verified = subprocess.run(
                [
                    ssh_keygen, "-Y", "verify", "-f", str(allowed_path),
                    "-I", authority_id, "-n", NAMESPACE, "-s",
                    str(signature_path),
                ],
                input=checksums, capture_output=True,
            )
    except PromotionRejected:
        raise
    except (OSError, subprocess.CalledProcessError, IndexError, UnicodeError):
        _unavailable()
    if verified.returncode != 0:
        _reject()


def _verify_release_promotion_snapshot(
    *, bundle_path: Path, signature_path: Path, registry_value: bytes,
    key_id: str, clock: Callable[[], datetime] | None = None,
    ssh_keygen: str = "ssh-keygen",
) -> dict[str, object]:
    if signature_path.name != bundle_path.name + ".sshsig":
        _reject()
    bundle = _read_regular(bundle_path)
    signature = _read_regular(signature_path)
    if len(signature) > 16_384 or not SSHSIG_RE.fullmatch(signature):
        _reject()
    registry = _registry(registry_value)
    authority_id, key = _current_key(registry, key_id)
    bundle_result, checksums = _bundle_snapshot(bundle, bundle_path.name)
    _fingerprint_and_verify(
        public_key=key["public_key"],
        expected_fingerprint=key["fingerprint"],
        authority_id=authority_id,
        signature=signature,
        checksums=checksums,
        ssh_keygen=ssh_keygen,
    )
    now = (clock or (lambda: datetime.now(timezone.utc)))()
    if not isinstance(now, datetime) or now.tzinfo is None:
        _unavailable()
    decided_at = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": 1,
        "bundle_filename": bundle_path.name,
        "bundle_sha256": _sha256(bundle),
        "checksums_sha256": _sha256(checksums),
        "signature_sha256": _sha256(signature),
        "source_commit": bundle_result["source_commit"],
        "package_version": bundle_result["package_version"],
        "bundle_format_version": bundle_result["bundle_format_version"],
        "signature_format": "SSHSIG-Ed25519",
        "namespace": NAMESPACE,
        "signer_authority_id": authority_id,
        "key_id": key_id,
        "key_fingerprint": key["fingerprint"],
        "policy_revision": registry["policy_revision"],
        "registry_sha256": _sha256(registry_value),
        "verification_identity": registry["verification_identity"],
        "decided_at": decided_at,
        "integrity": "verified",
        "signature": "verified",
        "authority": "current",
        "promotable": True,
    }


def verify_release_promotion(
    *, bundle_path: Path, signature_path: Path, registry_path: Path,
    key_id: str, clock: Callable[[], datetime] | None = None,
    ssh_keygen: str = "ssh-keygen",
) -> dict[str, object]:
    """Verify with the backward-compatible external registry-file boundary."""

    return _verify_release_promotion_snapshot(
        bundle_path=bundle_path,
        signature_path=signature_path,
        registry_value=_read_regular(registry_path, unavailable=True),
        key_id=key_id,
        clock=clock,
        ssh_keygen=ssh_keygen,
    )


def verify_release_promotion_with_projection(
    *, bundle_path: Path, signature_path: Path,
    registry_projection: CurrentReleaseAuthorityRegistryProjection,
    key_id: str, clock: Callable[[], datetime] | None = None,
    ssh_keygen: str = "ssh-keygen",
) -> dict[str, object]:
    """Verify against exactly one current system-of-record projection snapshot."""

    try:
        registry_value = registry_projection.project()
    except ReleaseRegistryProjectionUnavailable:
        _unavailable()
    except Exception:
        _unavailable()
    if registry_value is None:
        _reject()
    if type(registry_value) is not bytes or not registry_value:
        _unavailable()
    return _verify_release_promotion_snapshot(
        bundle_path=bundle_path,
        signature_path=signature_path,
        registry_value=registry_value,
        key_id=key_id,
        clock=clock,
        ssh_keygen=ssh_keygen,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release-promotion-verifier")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--key-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        evidence = verify_release_promotion(
            bundle_path=args.bundle,
            signature_path=args.signature,
            registry_path=args.registry,
            key_id=args.key_id,
        )
    except PromotionRejected:
        print(json.dumps({"error": "release_promotion_rejected"}))
        return 2
    except PromotionUnavailable:
        print(json.dumps({"error": "release_promotion_verification_unavailable"}))
        return 3
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
