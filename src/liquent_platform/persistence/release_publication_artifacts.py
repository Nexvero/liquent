"""Controlled local artifact source and pre-provider integrity verification."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Engine, text

from liquent_platform.identity.ports import (
    CurrentReleaseAuthorityRegistryProjection,
    ReleasePublicationArtifactSource,
)
from liquent_platform.identity.release_publication import (
    ReleasePublicationArtifactBinding,
    ReleasePublicationArtifactBytes,
    ReleasePublicationAttemptId,
    ReleasePublicationExecutionId,
    ReleasePublicationHandoffId,
    VerifiedReleasePublicationArtifacts,
)
from liquent_platform.persistence.identity_errors import (
    ReleasePublicationArtifactIntegrityUnavailable,
    ReleasePublicationArtifactSourceUnavailable,
)
from tools.release_promotion_verifier import (
    PromotionRejected,
    PromotionUnavailable,
    verify_release_promotion_with_projection,
)


_PREPARED = text(
    "SELECT execution.handoff_id,execution.bundle_sha256 AS execution_bundle_sha256,"
    " execution.signature_sha256 AS execution_signature_sha256,"
    " handoff.bundle_sha256,handoff.wheel_sha256,handoff.checksums_sha256,"
    " handoff.signature_sha256,handoff.promotion_evidence_sha256,"
    " handoff.source_commit,handoff.package_version,handoff.bundle_format_version,"
    " handoff.signer_authority_id,handoff.key_id,handoff.policy_revision_id,"
    " handoff.promotion_verifier_id,handoff.promotion_decided_at"
    " FROM release_publication_executions execution"
    " JOIN release_publication_execution_attempts attempt"
    " ON attempt.execution_id=execution.execution_id"
    " JOIN release_publication_handoffs handoff"
    " ON handoff.handoff_id=execution.handoff_id"
    " WHERE execution.execution_id=:execution AND attempt.attempt_id=:attempt"
    " AND execution.status='prepared' AND ("
    " (attempt.attempt_number=1 AND attempt.status='prepared'"
    " AND attempt.finished_at IS NULL) OR"
    " (attempt.attempt_number=1 AND attempt.status='reconciled'"
    " AND attempt.finished_at IS NOT NULL"
    " AND EXISTS (SELECT 1 FROM release_publication_recovery_decisions recovery"
    " WHERE recovery.execution_id=execution.execution_id"
    " AND recovery.attempt_id=attempt.attempt_id"
    " AND recovery.kind='absence_confirmed'"
    " AND recovery.current_authority IS TRUE)) OR"
    " (attempt.attempt_number=2 AND attempt.status='prepared'"
    " AND attempt.finished_at IS NULL"
    " AND EXISTS (SELECT 1 FROM release_publication_execution_attempts recovered"
    " JOIN release_publication_recovery_decisions recovery"
    " ON recovery.execution_id=recovered.execution_id"
    " AND recovery.attempt_id=recovered.attempt_id"
    " WHERE recovered.execution_id=execution.execution_id"
    " AND recovered.attempt_number=1 AND recovered.status='reconciled'"
    " AND recovered.finished_at IS NOT NULL"
    " AND recovery.kind='absence_confirmed'"
    " AND recovery.current_authority IS TRUE)))"
)


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _decode(value: object) -> str:
    if not isinstance(value, bytes) or not value:
        raise ReleasePublicationArtifactIntegrityUnavailable
    try:
        return bytes(value).decode("utf-8")
    except UnicodeError:
        raise ReleasePublicationArtifactIntegrityUnavailable from None


def _canonical_evidence(value: bytes) -> dict[str, object]:
    try:
        result = json.loads(value)
    except (UnicodeError, json.JSONDecodeError):
        raise ReleasePublicationArtifactIntegrityUnavailable from None
    if (
        not isinstance(result, dict)
        or result.get("promotable") is not True
        or value
        != (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    ):
        raise ReleasePublicationArtifactIntegrityUnavailable
    return result


def _iso(value: object) -> str:
    try:
        instant = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    except ValueError:
        raise ReleasePublicationArtifactIntegrityUnavailable from None
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _wheel_hash(bundle: bytes) -> str:
    try:
        with tarfile.open(fileobj=io.BytesIO(bundle), mode="r:gz") as archive:
            matches = [
                member for member in archive.getmembers()
                if member.isfile() and member.name.endswith("/manifest.json")
            ]
            if len(matches) != 1:
                raise ReleasePublicationArtifactIntegrityUnavailable
            opened = archive.extractfile(matches[0])
            if opened is None:
                raise ReleasePublicationArtifactIntegrityUnavailable
            manifest = json.loads(opened.read())
        value = manifest["wheel"]["sha256"]
        if type(value) is not str:
            raise ReleasePublicationArtifactIntegrityUnavailable
        return value
    except ReleasePublicationArtifactIntegrityUnavailable:
        raise
    except Exception:
        raise ReleasePublicationArtifactIntegrityUnavailable from None


@dataclass(frozen=True, slots=True)
class ReleasePublicationArtifactFiles:
    bundle_path: Path
    signature_path: Path
    promotion_evidence_path: Path


class BoundLocalReleasePublicationArtifactSource:
    """Read only preconfigured regular files for one exact hash binding."""

    __slots__ = ("_files",)

    def __init__(
        self,
        files: Mapping[
            ReleasePublicationArtifactBinding, ReleasePublicationArtifactFiles
        ],
    ) -> None:
        try:
            copied = dict(files)
            if not copied or any(
                type(binding) is not ReleasePublicationArtifactBinding
                or type(locations) is not ReleasePublicationArtifactFiles
                for binding, locations in copied.items()
            ):
                raise ReleasePublicationArtifactSourceUnavailable
            self._files = copied
        except ReleasePublicationArtifactSourceUnavailable:
            raise
        except Exception:
            raise ReleasePublicationArtifactSourceUnavailable from None

    def __repr__(self) -> str:
        return "BoundLocalReleasePublicationArtifactSource()"

    def load_artifacts(
        self, binding: ReleasePublicationArtifactBinding
    ) -> ReleasePublicationArtifactBytes:
        try:
            if type(binding) is not ReleasePublicationArtifactBinding:
                raise ReleasePublicationArtifactSourceUnavailable
            locations = self._files.get(binding)
            if locations is None:
                raise ReleasePublicationArtifactSourceUnavailable
            paths = (
                locations.bundle_path,
                locations.signature_path,
                locations.promotion_evidence_path,
            )
            if any(
                not isinstance(path, Path) or path.is_symlink() or not path.is_file()
                for path in paths
            ):
                raise ReleasePublicationArtifactSourceUnavailable
            bundle_name = locations.bundle_path.name
            if (
                not bundle_name
                or bundle_name in {".", ".."}
                or locations.signature_path.name != bundle_name + ".sshsig"
            ):
                raise ReleasePublicationArtifactSourceUnavailable
            return ReleasePublicationArtifactBytes(
                bundle_name,
                locations.bundle_path.read_bytes(),
                locations.signature_path.read_bytes(),
                locations.promotion_evidence_path.read_bytes(),
            )
        except ReleasePublicationArtifactSourceUnavailable:
            raise
        except Exception:
            raise ReleasePublicationArtifactSourceUnavailable from None


class DatabaseReleasePublicationArtifactIntegrityCheck:
    """Verify prepared bytes and current detached-signature authority read-only."""

    __slots__ = ("_engine", "_source", "_projection", "_clock", "_ssh_keygen")

    def __init__(
        self,
        engine: Engine,
        *,
        artifact_source: ReleasePublicationArtifactSource,
        registry_projection: CurrentReleaseAuthorityRegistryProjection,
        clock: Callable[[], datetime] | None = None,
        ssh_keygen: str = "ssh-keygen",
    ) -> None:
        self._engine = engine
        self._source = artifact_source
        self._projection = registry_projection
        self._clock = clock
        self._ssh_keygen = ssh_keygen

    def __repr__(self) -> str:
        return "DatabaseReleasePublicationArtifactIntegrityCheck()"

    def verify_artifacts(self, execution_id, attempt_id):
        try:
            if (
                type(execution_id) is not ReleasePublicationExecutionId
                or type(attempt_id) is not ReleasePublicationAttemptId
            ):
                raise ReleasePublicationArtifactIntegrityUnavailable
            with self._engine.connect() as connection:
                row = connection.execute(_PREPARED, {
                    "execution": execution_id.value.encode(),
                    "attempt": attempt_id.value.encode(),
                }).first()
            if row is None:
                return None
            return self._verify(execution_id, attempt_id, row)
        except ReleasePublicationArtifactIntegrityUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except (PromotionRejected,):
            return None
        except (PromotionUnavailable, ReleasePublicationArtifactSourceUnavailable):
            pass
        except Exception:
            pass
        raise ReleasePublicationArtifactIntegrityUnavailable

    def _verify(self, execution_id, attempt_id, row):
        if (
            row.execution_bundle_sha256 != row.bundle_sha256
            or row.execution_signature_sha256 != row.signature_sha256
        ):
            raise ReleasePublicationArtifactIntegrityUnavailable
        handoff_id = ReleasePublicationHandoffId(_decode(row.handoff_id))
        binding = ReleasePublicationArtifactBinding(
            handoff_id, row.bundle_sha256, row.signature_sha256,
            row.promotion_evidence_sha256,
        )
        artifacts = self._source.load_artifacts(binding)
        observed = (
            _hash(artifacts.bundle), _hash(artifacts.signature),
            _hash(artifacts.promotion_evidence),
        )
        expected = (
            row.bundle_sha256, row.signature_sha256,
            row.promotion_evidence_sha256,
        )
        if observed != expected:
            return None
        evidence = _canonical_evidence(artifacts.promotion_evidence)
        historical = {
            "bundle_sha256": row.bundle_sha256,
            "checksums_sha256": row.checksums_sha256,
            "signature_sha256": row.signature_sha256,
            "source_commit": row.source_commit,
            "package_version": row.package_version,
            "bundle_format_version": row.bundle_format_version,
            "signer_authority_id": _decode(row.signer_authority_id),
            "key_id": _decode(row.key_id),
            "policy_revision": _decode(row.policy_revision_id),
            "verification_identity": _decode(row.promotion_verifier_id),
            "decided_at": _iso(row.promotion_decided_at),
            "integrity": "verified", "signature": "verified",
            "authority": "current", "promotable": True,
        }
        if any(evidence.get(key) != value for key, value in historical.items()):
            return None
        with tempfile.TemporaryDirectory(prefix="liquent-publication-integrity-") as root:
            bundle_path = Path(root) / artifacts.bundle_filename
            signature_path = Path(root) / (artifacts.bundle_filename + ".sshsig")
            bundle_path.write_bytes(artifacts.bundle)
            signature_path.write_bytes(artifacts.signature)
            fresh = verify_release_promotion_with_projection(
                bundle_path=bundle_path,
                signature_path=signature_path,
                registry_projection=self._projection,
                key_id=_decode(row.key_id),
                clock=self._clock,
                ssh_keygen=self._ssh_keygen,
            )
        fresh_expected = {
            "bundle_sha256": row.bundle_sha256,
            "checksums_sha256": row.checksums_sha256,
            "signature_sha256": row.signature_sha256,
            "source_commit": row.source_commit,
            "package_version": row.package_version,
            "bundle_format_version": row.bundle_format_version,
            "signer_authority_id": _decode(row.signer_authority_id),
            "key_id": _decode(row.key_id),
            "integrity": "verified", "signature": "verified",
            "authority": "current", "promotable": True,
        }
        if any(fresh.get(key) != value for key, value in fresh_expected.items()):
            return None
        wheel_hash = _wheel_hash(artifacts.bundle)
        if wheel_hash != row.wheel_sha256:
            return None
        return VerifiedReleasePublicationArtifacts(
            execution_id, attempt_id, handoff_id, row.package_version,
            row.bundle_sha256, row.wheel_sha256, row.checksums_sha256,
            row.signature_sha256, row.promotion_evidence_sha256, artifacts,
        )
