"""Canonical codec and atomic private file for one wrapper job binding."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat

from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffExecutionClaimId,
    ManifestHandoffExecutionOwnerId,
    ManifestHandoffName,
    ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryOwnerId,
    ManifestHandoffRegistryScopeId,
    ManifestHandoffScopeBinding,
)
from liquent_platform.identity.manifest_handoff_supervisor import (
    ManifestHandoffRecoverySupervisorRequest,
    ManifestHandoffSupervisorHandleId,
    ManifestHandoffWriterSupervisorRequest,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_artifact import (
    ManifestHandoffSupervisorControlArtifactBytes,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorTerminalObservationId,
)
from liquent_platform.identity.manifest_handoff_supervisor_engine import (
    ManifestHandoffSupervisorEngineProfile,
)
from liquent_platform.identity.manifest_handoff_supervisor_gate_wrapper import (
    StartManifestHandoffSupervisorGateWrapper,
)
from liquent_platform.identity.manifest_handoff_supervisor_job_document import (
    EncodedManifestHandoffSupervisorJobDocument,
    ManifestHandoffSupervisorJobDocument,
    ManifestHandoffSupervisorJobDocumentConflict,
    PublishedManifestHandoffSupervisorJobDocument,
    PublishManifestHandoffSupervisorJobDocument,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffSupervisorGatedObservationId,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactFacts,
    ManifestHandoffSupervisorControlArtifactId,
    ManifestHandoffSupervisorControlDirectoryId,
    ManifestHandoffSupervisorImageDigest,
    ManifestHandoffSupervisorRuntimeContainerId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_SCHEMA = "liquent.manifest-handoff-supervisor-job"
_VERSION = 1
_NAME = "job-binding.json"
_MAXIMUM = 65_536
_KEYS = {
    "schema", "version", "document_id", "handle_id", "control_directory_id",
    "profile", "runtime_container_id", "image_digest", "ready_artifact_id",
    "gated_observation_id", "consumed_artifact_id", "terminal_artifact_id",
    "terminal_observation_id", "claim_id", "owner_id", "scope_id",
    "source_root", "target_root", "handoff_name",
}


class CanonicalManifestHandoffSupervisorJobDocumentCodec:
    def encode(self, document):
        if type(document) is not ManifestHandoffSupervisorJobDocument:
            raise ManifestHandoffRegistryUnavailable
        try:
            gate, request = document.gate, document.request
            value = {
                "schema": _SCHEMA,
                "version": _VERSION,
                "document_id": document.document_id.value,
                "handle_id": gate.handle_id.value,
                "control_directory_id": gate.control_directory_id.value,
                "profile": gate.profile.value,
                "runtime_container_id": document.runtime_container_id.value,
                "image_digest": document.image_digest.value,
                "ready_artifact_id": gate.ready_artifact_id.value,
                "gated_observation_id": gate.gated_observation_id.value,
                "consumed_artifact_id": gate.consumed_artifact_id.value,
                "terminal_artifact_id": gate.terminal_artifact_id.value,
                "terminal_observation_id": gate.terminal_observation_id.value,
                "claim_id": request.claim_id.value,
                "owner_id": request.owner_id.value,
                "scope_id": request.binding.scope_id.value,
                "source_root": str(request.binding.source_root),
                "target_root": str(request.binding.target_root),
                "handoff_name": request.handoff_name.value,
            }
            content = json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                allow_nan=False,
            ).encode("utf-8")
            facts = ManifestHandoffSupervisorControlArtifactFacts(
                hashlib.sha256(content).hexdigest(), len(content)
            )
            return EncodedManifestHandoffSupervisorJobDocument(
                document, ManifestHandoffSupervisorControlArtifactBytes(content), facts
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def decode(self, encoded):
        if type(encoded) is not EncodedManifestHandoffSupervisorJobDocument:
            raise ManifestHandoffRegistryUnavailable
        decoded = self.decode_content(encoded.content.value)
        if decoded != encoded.document or self.encode(decoded).content != encoded.content:
            raise ManifestHandoffRegistryUnavailable
        return decoded

    def decode_content(self, content):
        try:
            if type(content) is not bytes or not content or len(content) > _MAXIMUM:
                raise ManifestHandoffRegistryUnavailable
            value = json.loads(content.decode("utf-8"), object_pairs_hook=_unique)
            if (
                type(value) is not dict or set(value) != _KEYS
                or value["schema"] != _SCHEMA or type(value["version"]) is not int
                or value["version"] != _VERSION
            ):
                raise ManifestHandoffRegistryUnavailable
            profile = ManifestHandoffSupervisorEngineProfile(value["profile"])
            handle = ManifestHandoffSupervisorHandleId(value["handle_id"])
            gate = StartManifestHandoffSupervisorGateWrapper(
                handle,
                ManifestHandoffSupervisorControlDirectoryId(value["control_directory_id"]),
                profile,
                ManifestHandoffSupervisorControlArtifactId(value["ready_artifact_id"]),
                ManifestHandoffSupervisorGatedObservationId(value["gated_observation_id"]),
                ManifestHandoffSupervisorControlArtifactId(value["consumed_artifact_id"]),
                ManifestHandoffSupervisorControlArtifactId(value["terminal_artifact_id"]),
                ManifestHandoffSupervisorTerminalObservationId(value["terminal_observation_id"]),
            )
            binding = ManifestHandoffScopeBinding(
                ManifestHandoffRegistryScopeId(value["scope_id"]),
                Path(value["source_root"]), Path(value["target_root"]),
            )
            name = ManifestHandoffName(value["handoff_name"])
            if profile is ManifestHandoffSupervisorEngineProfile.WRITER:
                request = ManifestHandoffWriterSupervisorRequest(
                    ManifestHandoffExecutionClaimId(value["claim_id"]),
                    ManifestHandoffExecutionOwnerId(value["owner_id"]), binding, name,
                )
            else:
                request = ManifestHandoffRecoverySupervisorRequest(
                    ManifestHandoffRecoveryClaimId(value["claim_id"]),
                    ManifestHandoffRecoveryOwnerId(value["owner_id"]), binding, name,
                )
            result = ManifestHandoffSupervisorJobDocument(
                ManifestHandoffSupervisorControlArtifactId(value["document_id"]), gate,
                ManifestHandoffSupervisorRuntimeContainerId(value["runtime_container_id"]),
                ManifestHandoffSupervisorImageDigest(value["image_digest"]), request,
            )
            if self.encode(result).content.value != content:
                raise ManifestHandoffRegistryUnavailable
            return result
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None


class AtomicLocalManifestHandoffSupervisorJobDocuments:
    __slots__ = ("_root", "_resolve", "_codec")

    def __init__(
        self, root: Path, *,
        resolve_directory: Callable[[ManifestHandoffSupervisorControlDirectoryId], Path | None],
        codec: CanonicalManifestHandoffSupervisorJobDocumentCodec,
    ) -> None:
        if (
            not isinstance(root, Path) or not root.is_absolute()
            or not callable(resolve_directory)
            or type(codec) is not CanonicalManifestHandoffSupervisorJobDocumentCodec
        ):
            raise ManifestHandoffRegistryUnavailable
        self._root, self._resolve, self._codec = root, resolve_directory, codec

    def __repr__(self) -> str:
        return "AtomicLocalManifestHandoffSupervisorJobDocuments()"

    def publish(self, request):
        if type(request) is not PublishManifestHandoffSupervisorJobDocument:
            raise ManifestHandoffRegistryUnavailable
        encoded = request.document
        directory = self._directory(encoded.document.gate.control_directory_id)
        descriptor = temporary_fd = None
        temporary = ".pending-job-" + secrets.token_hex(16)
        try:
            descriptor = self._open_directory(directory)
            current = self._read_optional(descriptor)
            if current is not None:
                return self._same_or_conflict(encoded, current)
            temporary_fd = os.open(
                temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600, dir_fd=descriptor,
            )
            _write_all(temporary_fd, encoded.content.value)
            os.fsync(temporary_fd)
            os.close(temporary_fd)
            temporary_fd = None
            try:
                os.link(
                    temporary, _NAME, src_dir_fd=descriptor, dst_dir_fd=descriptor,
                    follow_symlinks=False,
                )
            except FileExistsError:
                current = self._read(descriptor)
                return self._same_or_conflict(encoded, current)
            finally:
                os.unlink(temporary, dir_fd=descriptor)
                temporary = ""
            os.fsync(descriptor)
            return PublishedManifestHandoffSupervisorJobDocument(
                encoded.document.document_id, encoded.facts
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if temporary_fd is not None:
                os.close(temporary_fd)
            if descriptor is not None:
                if temporary:
                    try:
                        os.unlink(temporary, dir_fd=descriptor)
                    except FileNotFoundError:
                        pass
                os.close(descriptor)

    def read(self, directory_id):
        if type(directory_id) is not ManifestHandoffSupervisorControlDirectoryId:
            raise ManifestHandoffRegistryUnavailable
        descriptor = None
        try:
            descriptor = self._open_directory(self._directory(directory_id))
            try:
                content = self._read(descriptor)
            except FileNotFoundError:
                return None
            return self._codec.decode_content(content)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def _same_or_conflict(self, encoded, current):
        if current != encoded.content.value:
            return ManifestHandoffSupervisorJobDocumentConflict()
        decoded = self._codec.decode_content(current)
        if decoded != encoded.document:
            raise ManifestHandoffRegistryUnavailable
        return PublishedManifestHandoffSupervisorJobDocument(
            encoded.document.document_id, encoded.facts
        )

    def _directory(self, directory_id):
        try:
            path = self._resolve(directory_id)
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        if not isinstance(path, Path) or not path.is_absolute() or path.parent != self._root:
            raise ManifestHandoffRegistryUnavailable
        return path

    def _open_directory(self, path):
        root = directory = None
        try:
            root = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            directory = os.open(
                path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root
            )
            facts = os.fstat(directory)
            if (
                not stat.S_ISDIR(facts.st_mode) or facts.st_uid != os.geteuid()
                or stat.S_IMODE(facts.st_mode) != 0o700
            ):
                raise ManifestHandoffRegistryUnavailable
            return directory
        except ManifestHandoffRegistryUnavailable:
            if directory is not None:
                os.close(directory)
            raise
        except Exception:
            if directory is not None:
                os.close(directory)
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if root is not None:
                os.close(root)

    def _read_optional(self, directory):
        try:
            return self._read(directory)
        except FileNotFoundError:
            return None

    @staticmethod
    def _read(directory):
        descriptor = os.open(_NAME, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        try:
            facts = os.fstat(descriptor)
            if (
                not stat.S_ISREG(facts.st_mode) or facts.st_uid != os.geteuid()
                or stat.S_IMODE(facts.st_mode) != 0o600 or facts.st_nlink != 1
                or facts.st_size < 1 or facts.st_size > _MAXIMUM
            ):
                raise ManifestHandoffRegistryUnavailable
            content = bytearray()
            while len(content) <= _MAXIMUM:
                part = os.read(descriptor, min(8192, _MAXIMUM + 1 - len(content)))
                if not part:
                    break
                content.extend(part)
            if not content or len(content) > _MAXIMUM:
                raise ManifestHandoffRegistryUnavailable
            return bytes(content)
        finally:
            os.close(descriptor)


def _write_all(descriptor: int, content: bytes) -> None:
    offset = 0
    while offset < len(content):
        written = os.write(descriptor, content[offset:])
        if written <= 0:
            raise ManifestHandoffRegistryUnavailable
        offset += written


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ManifestHandoffRegistryUnavailable
        value[key] = item
    return value
