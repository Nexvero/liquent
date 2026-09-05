"""Canonical codec and atomic local files for supervisor control artifacts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat

from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffExecutionClaimId, ManifestHandoffExecutionOwnerId,
    ManifestHandoffFacts, ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryOwnerId,
)
from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess, CompletedManifestHandoffWriterProcess,
    ManifestHandoffRecoveryProcessKind, ManifestHandoffSupervisorHandleId,
    ManifestHandoffWriterProcessKind,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    EncodedManifestHandoffSupervisorControlArtifact,
    ManifestHandoffSupervisorControlArtifactBytes,
    ManifestHandoffSupervisorControlArtifactConflict,
    ManifestHandoffSupervisorReadyDocument,
    ManifestHandoffSupervisorReleaseConsumedDocument,
    ManifestHandoffSupervisorReleaseTokenDocument,
    ManifestHandoffSupervisorTerminalEnvelopeDocument,
    PublishManifestHandoffSupervisorControlArtifact,
    PublishedManifestHandoffSupervisorControlArtifact,
    ReadManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorReleaseId, ManifestHandoffSupervisorTerminalObservationId,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import ManifestHandoffSupervisorGatedObservationId
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactFacts,
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlArtifactRole,
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_SCHEMA = "liquent.manifest-handoff-control"
_VERSION = 1
_NAMES = {
    ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY: "wrapper-ready.json",
    ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN: "release-token.json",
    ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED: "release-consumed.json",
    ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE: "terminal-envelope.json",
}
_BASE_KEYS = {"schema", "version", "artifact_id", "handle_id", "role", "correlation_id"}


def canonical_manifest_handoff_supervisor_control_artifact_name(role):
    if type(role) is not ManifestHandoffSupervisorControlArtifactRole:
        raise ManifestHandoffRegistryUnavailable
    return _NAMES[role]


class CanonicalManifestHandoffSupervisorControlArtifactCodec:
    def encode(self, document):
        try:
            value = {"schema": _SCHEMA, "version": _VERSION,
                "artifact_id": document.artifact_id.value, "handle_id": document.handle_id.value,
                "role": document.role.value, "correlation_id": document.correlation_id.value}
            if type(document) is ManifestHandoffSupervisorTerminalEnvelopeDocument:
                value["outcome"] = self._encode_outcome(document.outcome)
            elif type(document) not in (ManifestHandoffSupervisorReadyDocument,
                    ManifestHandoffSupervisorReleaseTokenDocument,
                    ManifestHandoffSupervisorReleaseConsumedDocument):
                raise ManifestHandoffRegistryUnavailable
            content = json.dumps(value, sort_keys=True, separators=(",", ":"),
                ensure_ascii=True, allow_nan=False).encode("utf-8")
            return self._encoded(document.artifact_id, document.handle_id, document.role, content)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def decode(self, artifact):
        if type(artifact) is not EncodedManifestHandoffSupervisorControlArtifact:
            raise ManifestHandoffRegistryUnavailable
        document = self.decode_content(artifact.content.value)
        if (document.artifact_id != artifact.artifact_id
                or document.handle_id != artifact.handle_id or document.role is not artifact.role
                or self.encode(document).content != artifact.content):
            raise ManifestHandoffRegistryUnavailable
        return document

    def decode_content(self, content):
        try:
            if type(content) is not bytes:
                raise ManifestHandoffRegistryUnavailable
            value = json.loads(content.decode("utf-8"), object_pairs_hook=self._unique)
            if (type(value) is not dict or type(value.get("schema")) is not str
                    or value.get("schema") != _SCHEMA or type(value.get("version")) is not int
                    or value.get("version") != _VERSION):
                raise ManifestHandoffRegistryUnavailable
            role = ManifestHandoffSupervisorControlArtifactRole(value.get("role"))
            keys = _BASE_KEYS | ({"outcome"} if role is ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE else set())
            if set(value) != keys:
                raise ManifestHandoffRegistryUnavailable
            artifact_id = ManifestHandoffSupervisorControlArtifactId(value["artifact_id"])
            handle_id = ManifestHandoffSupervisorHandleId(value["handle_id"])
            correlation = value["correlation_id"]
            if role is ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY:
                result = ManifestHandoffSupervisorReadyDocument(artifact_id, handle_id, ManifestHandoffSupervisorGatedObservationId(correlation))
            elif role is ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN:
                result = ManifestHandoffSupervisorReleaseTokenDocument(artifact_id, handle_id, ManifestHandoffSupervisorReleaseId(correlation))
            elif role is ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED:
                result = ManifestHandoffSupervisorReleaseConsumedDocument(artifact_id, handle_id, ManifestHandoffSupervisorReleaseId(correlation))
            else:
                result = ManifestHandoffSupervisorTerminalEnvelopeDocument(artifact_id, handle_id,
                    ManifestHandoffSupervisorTerminalObservationId(correlation), self._decode_outcome(value["outcome"], handle_id))
            if self.encode(result).content.value != content:
                raise ManifestHandoffRegistryUnavailable
            return result
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ManifestHandoffRegistryUnavailable
            result[key] = value
        return result

    @staticmethod
    def _encoded(artifact_id, handle_id, role, content):
        digest = hashlib.sha256(content).hexdigest()
        return EncodedManifestHandoffSupervisorControlArtifact(artifact_id, handle_id, role,
            ManifestHandoffSupervisorControlArtifactBytes(content),
            ManifestHandoffSupervisorControlArtifactFacts(digest, len(content)))

    @staticmethod
    def _instant(value):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def _encode_outcome(self, outcome):
        writer = type(outcome) is CompletedManifestHandoffWriterProcess
        if not writer and type(outcome) is not CompletedManifestHandoffRecoveryProcess:
            raise ManifestHandoffRegistryUnavailable
        facts = None if outcome.facts is None else {
            "manifest_sha256": outcome.facts.manifest_sha256, "file_count": outcome.facts.file_count}
        return {"process": "writer" if writer else "recovery",
            "claim_id": outcome.claim_id.value, "owner_id": outcome.owner_id.value,
            "kind": outcome.kind.value, "ended_at": self._instant(outcome.ended_at),
            "filename": outcome.filename, "facts": facts}

    def _decode_outcome(self, value, handle_id):
        keys = {"process", "claim_id", "owner_id", "kind", "ended_at", "filename", "facts"}
        if type(value) is not dict or set(value) != keys:
            raise ManifestHandoffRegistryUnavailable
        ended = datetime.fromisoformat(value["ended_at"].replace("Z", "+00:00"))
        facts_value = value["facts"]
        if facts_value is None: facts = None
        elif type(facts_value) is dict and set(facts_value) == {"manifest_sha256", "file_count"}:
            facts = ManifestHandoffFacts(facts_value["manifest_sha256"], facts_value["file_count"])
        else: raise ManifestHandoffRegistryUnavailable
        if value["process"] == "writer":
            return CompletedManifestHandoffWriterProcess(handle_id,
                ManifestHandoffExecutionClaimId(value["claim_id"]), ManifestHandoffExecutionOwnerId(value["owner_id"]),
                ManifestHandoffWriterProcessKind(value["kind"]), ended, value["filename"], facts)
        if value["process"] == "recovery":
            return CompletedManifestHandoffRecoveryProcess(handle_id,
                ManifestHandoffRecoveryClaimId(value["claim_id"]), ManifestHandoffRecoveryOwnerId(value["owner_id"]),
                ManifestHandoffRecoveryProcessKind(value["kind"]), ended, value["filename"], facts)
        raise ManifestHandoffRegistryUnavailable


class AtomicLocalManifestHandoffSupervisorControlArtifacts:
    __slots__ = ("_root", "_resolve", "_codec")

    def __init__(self, root: Path, *, resolve_directory: Callable[[ManifestHandoffSupervisorControlDirectoryId], Path],
                 codec: CanonicalManifestHandoffSupervisorControlArtifactCodec) -> None:
        if not isinstance(root, Path) or not root.is_absolute() or type(codec) is not CanonicalManifestHandoffSupervisorControlArtifactCodec:
            raise ManifestHandoffRegistryUnavailable
        self._root, self._resolve, self._codec = root, resolve_directory, codec

    def __repr__(self): return "AtomicLocalManifestHandoffSupervisorControlArtifacts()"

    def publish(self, request):
        if type(request) is not PublishManifestHandoffSupervisorControlArtifact:
            raise ManifestHandoffRegistryUnavailable
        directory = self._directory(request.control_directory_id)
        descriptor = None; temporary = ".pending-" + secrets.token_hex(16)
        try:
            descriptor = self._open_directory(directory)
            final = canonical_manifest_handoff_supervisor_control_artifact_name(request.artifact.role)
            try:
                current = self._read(descriptor, final)
            except FileNotFoundError:
                current = None
            if current is not None:
                if current != request.artifact.content.value:
                    return ManifestHandoffSupervisorControlArtifactConflict()
                return self._published(request)
            temporary_fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=descriptor)
            try:
                self._write_all(temporary_fd, request.artifact.content.value); os.fsync(temporary_fd)
            finally: os.close(temporary_fd)
            try:
                os.link(temporary, final, src_dir_fd=descriptor, dst_dir_fd=descriptor, follow_symlinks=False)
            except FileExistsError:
                current = self._read(descriptor, final)
                os.unlink(temporary, dir_fd=descriptor); temporary = None
                os.fsync(descriptor)
                if current != request.artifact.content.value:
                    return ManifestHandoffSupervisorControlArtifactConflict()
                return self._published(request)
            os.unlink(temporary, dir_fd=descriptor); temporary = None
            os.fsync(descriptor)
            return self._published(request)
        except Exception as error:
            if isinstance(error, ManifestHandoffRegistryUnavailable): raise
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if descriptor is not None:
                if temporary is not None:
                    try: os.unlink(temporary, dir_fd=descriptor)
                    except FileNotFoundError: pass
                    except OSError: pass
                os.close(descriptor)

    def read(self, request):
        if type(request) is not ReadManifestHandoffSupervisorControlArtifact:
            raise ManifestHandoffRegistryUnavailable
        descriptor = None
        try:
            descriptor = self._open_directory(self._directory(request.control_directory_id))
            try: content = self._read(descriptor, canonical_manifest_handoff_supervisor_control_artifact_name(request.role))
            except FileNotFoundError: return None
            document = self._codec.decode_content(content)
            if document.role is not request.role: raise ManifestHandoffRegistryUnavailable
            return self._codec.encode(document)
        except ManifestHandoffRegistryUnavailable: raise
        except Exception: raise ManifestHandoffRegistryUnavailable from None
        finally:
            if descriptor is not None: os.close(descriptor)

    def _directory(self, directory_id):
        try: path = self._resolve(directory_id)
        except Exception: raise ManifestHandoffRegistryUnavailable from None
        if not isinstance(path, Path) or not path.is_absolute() or path.parent != self._root or path.name in ("", ".", ".."):
            raise ManifestHandoffRegistryUnavailable
        return path

    def _open_directory(self, path):
        root = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            self._validate_directory(root)
            descriptor = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
        finally: os.close(root)
        try: self._validate_directory(descriptor)
        except Exception:
            os.close(descriptor); raise
        return descriptor

    @staticmethod
    def _validate_directory(descriptor):
        facts = os.fstat(descriptor)
        if (not stat.S_ISDIR(facts.st_mode) or facts.st_uid != os.geteuid()
                or stat.S_IMODE(facts.st_mode) != 0o700):
            raise ManifestHandoffRegistryUnavailable

    @staticmethod
    def _read(directory, name):
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        try:
            facts = os.fstat(descriptor)
            if (not stat.S_ISREG(facts.st_mode) or facts.st_uid != os.geteuid()
                    or stat.S_IMODE(facts.st_mode) != 0o600 or facts.st_nlink != 1):
                raise ManifestHandoffRegistryUnavailable
            chunks=[]; remaining=65_537
            while remaining:
                chunk=os.read(descriptor, remaining)
                if not chunk: break
                chunks.append(chunk); remaining -= len(chunk)
            content=b"".join(chunks)
            if not content or len(content) > 65_536: raise ManifestHandoffRegistryUnavailable
            return content
        finally: os.close(descriptor)

    @staticmethod
    def _write_all(descriptor, content):
        view=memoryview(content)
        while view:
            written=os.write(descriptor, view)
            if written < 1: raise ManifestHandoffRegistryUnavailable
            view=view[written:]

    @staticmethod
    def _published(request):
        return PublishedManifestHandoffSupervisorControlArtifact(request.control_directory_id,
            request.artifact.artifact_id, request.artifact.role, request.artifact.facts)


class DirectAtomicLocalManifestHandoffSupervisorControlArtifacts(
    AtomicLocalManifestHandoffSupervisorControlArtifacts
):
    """Bind one child-visible artifact directory to one control-directory ID."""

    __slots__ = ("_bound_directory_id", "_direct_directory")

    def __init__(self, directory: Path, *,
                 control_directory_id: ManifestHandoffSupervisorControlDirectoryId,
                 codec: CanonicalManifestHandoffSupervisorControlArtifactCodec) -> None:
        if (not isinstance(directory, Path) or not directory.is_absolute()
                or directory.name in ("", ".", "..")
                or type(control_directory_id)
                is not ManifestHandoffSupervisorControlDirectoryId
                or type(codec)
                is not CanonicalManifestHandoffSupervisorControlArtifactCodec):
            raise ManifestHandoffRegistryUnavailable
        self._root = directory.parent
        self._resolve = None
        self._codec = codec
        self._bound_directory_id = control_directory_id
        self._direct_directory = directory

    def __repr__(self) -> str:
        return "DirectAtomicLocalManifestHandoffSupervisorControlArtifacts()"

    def _directory(self, directory_id):
        if (type(directory_id) is not ManifestHandoffSupervisorControlDirectoryId
                or directory_id != self._bound_directory_id):
            raise ManifestHandoffRegistryUnavailable
        return self._direct_directory

    def _open_directory(self, path):
        if path != self._direct_directory:
            raise ManifestHandoffRegistryUnavailable
        descriptor = None
        try:
            descriptor = os.open(
                path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
            self._validate_directory(descriptor)
            return descriptor
        except ManifestHandoffRegistryUnavailable:
            if descriptor is not None:
                os.close(descriptor)
            raise
        except Exception:
            if descriptor is not None:
                os.close(descriptor)
            raise ManifestHandoffRegistryUnavailable from None
