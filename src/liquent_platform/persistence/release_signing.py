"""Persistent current-authority-bound signing of one release candidate."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.ports import (
    ReleaseSignatureVerifier,
    ReleaseSigningKeyProvider,
)
from liquent_platform.identity.release_authority import (
    ReleaseRegistrySetRevisionId,
    ReleaseSigningDecisionId,
    ReleaseSigningExecutorId,
    ReleaseSigningKeyId,
    SignedReleaseCandidate,
)
from liquent_platform.persistence.identity_errors import (
    ReleaseSigningConflict,
    ReleaseSigningUnavailable,
)
from tools.operational_release_bundle import BundleRejected, verify_bundle


NAMESPACE = "liquent-operations-release-v1"
_LOCK = text(
    "LOCK TABLE release_registry_current_set,release_registry_set_revisions,"
    " release_registry_revision_signers,release_registry_revision_keys,"
    " release_signing_keys,release_signing_decisions IN SHARE ROW EXCLUSIVE MODE"
)
_RETRY = text("SELECT * FROM release_signing_decisions WHERE decision_id=:decision")
_CURRENT = text(
    "SELECT revision.policy_revision_id,key.signer_authority_id,key.fingerprint,"
    " key.public_key FROM release_registry_current_set AS current"
    " JOIN release_registry_set_revisions AS revision"
    " ON revision.revision_id=current.revision_id AND revision.policy_status='active'"
    " JOIN release_registry_revision_keys AS member"
    " ON member.revision_id=current.revision_id AND member.key_id=:key"
    " AND member.status='active' JOIN release_signing_keys AS key"
    " ON key.key_id=member.key_id AND key.signer_authority_id=member.signer_authority_id"
    " AND key.algorithm='ssh-ed25519' AND key.namespace=:namespace"
    " JOIN release_registry_revision_signers AS signer"
    " ON signer.revision_id=current.revision_id"
    " AND signer.authority_id=key.signer_authority_id AND signer.status='active'"
    " WHERE current.singleton_key=1 AND current.revision_id=:expected"
)


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _encode(value: str) -> bytes:
    if type(value) is not str or not value:
        raise ReleaseSigningUnavailable
    return value.encode("utf-8")


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleaseSigningUnavailable
    return bytes(value).decode("utf-8")


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _snapshot(path: Path) -> tuple[bytes, bytes, dict[str, object]]:
    try:
        if path.is_symlink() or not path.is_file():
            raise ReleaseSigningUnavailable
        bundle = path.read_bytes()
        with tempfile.TemporaryDirectory(prefix="liquent-signing-") as directory:
            copy = Path(directory) / path.name
            copy.write_bytes(bundle)
            result = verify_bundle(copy)
        checksums = []
        with tarfile.open(fileobj=io.BytesIO(bundle), mode="r:gz") as archive:
            for member in archive.getmembers():
                if member.isfile() and member.name.endswith("/SHA256SUMS"):
                    item = archive.extractfile(member)
                    if item is not None:
                        checksums.append(item.read())
        if len(checksums) != 1:
            raise ReleaseSigningUnavailable
        return bundle, checksums[0], result
    except ReleaseSigningUnavailable:
        raise
    except (BundleRejected, OSError, tarfile.TarError):
        raise ReleaseSigningUnavailable


class DatabaseReleaseSigning:
    """Resolve current trust, sign, verify, and persist one immutable decision."""

    __slots__ = ("_engine", "_executor", "_provider", "_verifier", "_clock")

    def __init__(
        self, engine: Engine, *, executor_id: ReleaseSigningExecutorId,
        key_provider: ReleaseSigningKeyProvider,
        signature_verifier: ReleaseSignatureVerifier,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if type(executor_id) is not ReleaseSigningExecutorId:
            raise ValueError("release signing executor is invalid")
        self._engine = engine
        self._executor = executor_id
        self._provider = key_provider
        self._verifier = signature_verifier
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseReleaseSigning()"

    def sign_candidate(
        self, decision_id: ReleaseSigningDecisionId, key_id: ReleaseSigningKeyId,
        expected_revision: ReleaseRegistrySetRevisionId, bundle_path: str,
    ) -> SignedReleaseCandidate | None:
        try:
            if (type(decision_id) is not ReleaseSigningDecisionId
                or type(key_id) is not ReleaseSigningKeyId
                or type(expected_revision) is not ReleaseRegistrySetRevisionId
                or type(bundle_path) is not str or not bundle_path):
                raise ReleaseSigningUnavailable
            bundle, checksums, manifest = _snapshot(Path(bundle_path))
            values = {
                "decision": _encode(decision_id.value), "key": _encode(key_id.value),
                "expected": _encode(expected_revision.value), "namespace": NAMESPACE,
                "bundle_hash": _hash(bundle), "checksums_hash": _hash(checksums),
            }
            with self._engine.begin() as transaction:
                return self._sign(transaction, decision_id, key_id, expected_revision,
                                  checksums, manifest, values)
        except (ReleaseSigningConflict, ReleaseSigningUnavailable) as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ReleaseSigningUnavailable

    def _sign(self, transaction: Connection, decision_id, key_id, expected,
              checksums: bytes, manifest: dict[str, object], values: dict[str, object]):
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise ReleaseSigningUnavailable
        retry = transaction.execute(_RETRY, values).first()
        if retry is not None:
            if (retry.bundle_sha256 != values["bundle_hash"]
                or bytes(retry.key_id) != values["key"]
                or bytes(retry.registry_revision_id) != values["expected"]):
                raise ReleaseSigningConflict
            return SignedReleaseCandidate(decision_id, bytes(retry.signature), bytes(retry.evidence))
        current = transaction.execute(_CURRENT, values).first()
        if current is None:
            return None
        fingerprint = self._provider.fingerprint()
        if fingerprint != current.fingerprint:
            return None
        signature = self._provider.sign(checksums, NAMESPACE)
        if type(signature) is not bytes or not signature:
            raise ReleaseSigningUnavailable
        authority = _decode(current.signer_authority_id)
        if self._verifier.verify(current.public_key, authority, checksums, signature) is not True:
            raise ReleaseSigningUnavailable
        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ReleaseSigningUnavailable
        now = now.astimezone(timezone.utc)
        evidence = _canonical({
            "schema_version": 1, "decision_id": decision_id.value,
            "bundle_sha256": values["bundle_hash"],
            "checksums_sha256": values["checksums_hash"],
            "signature_sha256": _hash(signature),
            "source_commit": manifest["source_commit"],
            "package_version": manifest["package_version"],
            "signer_authority_id": authority, "key_id": key_id.value,
            "key_fingerprint": fingerprint,
            "registry_revision_id": expected.value,
            "policy_revision_id": _decode(current.policy_revision_id),
            "signature_format": "SSHSIG-Ed25519", "namespace": NAMESPACE,
            "executor_identity": self._executor.value,
            "decided_at": now.isoformat().replace("+00:00", "Z"),
            "outcome": "signed",
        })
        values.update({
            "signature_hash": _hash(signature), "commit": manifest["source_commit"],
            "version": manifest["package_version"], "authority": current.signer_authority_id,
            "fingerprint": fingerprint, "policy": current.policy_revision_id,
            "executor": _encode(self._executor.value), "now": now,
            "signature": signature, "evidence": evidence,
        })
        transaction.execute(text(
            "INSERT INTO release_signing_decisions VALUES (:decision,:bundle_hash,"
            ":checksums_hash,:signature_hash,:commit,:version,:authority,:key,"
            ":fingerprint,:expected,:policy,'SSHSIG-Ed25519',:namespace,:executor,"
            ":now,:signature,:evidence)"
        ), values)
        return SignedReleaseCandidate(decision_id, signature, evidence)
