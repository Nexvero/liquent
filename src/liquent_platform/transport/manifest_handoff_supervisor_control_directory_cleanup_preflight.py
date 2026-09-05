"""Read-only local preflight for supervisor control-directory cleanup."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import os
from pathlib import Path
import secrets
import stat

from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    CleanupManifestHandoffSupervisorControlDirectory,
    ManifestHandoffSupervisorControlDirectoryCleanupConflict,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_clearance import (
    ClearedManifestHandoffSupervisorControlDirectoryCleanup,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_execution import (
    AbsentManifestHandoffSupervisorControlDirectoryCleanupPreflight,
    ManifestHandoffSupervisorControlDirectoryCleanupPreflightId,
    PreflightManifestHandoffSupervisorControlDirectoryCleanup,
    PreparedManifestHandoffSupervisorControlDirectoryCleanup,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlArtifactRole,
    RecordedManifestHandoffSupervisorControlArtifact,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_control_artifacts import (
    CanonicalManifestHandoffSupervisorControlArtifactCodec,
    canonical_manifest_handoff_supervisor_control_artifact_name,
)


_ROLES = tuple(ManifestHandoffSupervisorControlArtifactRole)
_OPEN_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_OPEN_FILE = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
_MAX_BYTES = 65_536


class SafeLocalManifestHandoffSupervisorControlDirectoryCleanupPreflight:
    """Inventory one current cleared retired leaf without mutating it."""

    __slots__ = (
        "_root", "_attempts", "_clearances", "_artifacts", "_codec", "_clock",
        "_preflight",
    )

    def __init__(
        self,
        root: Path,
        *,
        attempt_lookup: Callable,
        clearance_lookup: Callable,
        artifact_lookup: Callable,
        codec: CanonicalManifestHandoffSupervisorControlArtifactCodec,
        clock: Callable[[], datetime] | None = None,
        preflight_id_generator: Callable[[], str] | None = None,
    ) -> None:
        if (
            not isinstance(root, Path)
            or not root.is_absolute()
            or not callable(attempt_lookup)
            or not callable(clearance_lookup)
            or not callable(artifact_lookup)
            or type(codec) is not CanonicalManifestHandoffSupervisorControlArtifactCodec
            or (clock is not None and not callable(clock))
            or (preflight_id_generator is not None and not callable(preflight_id_generator))
        ):
            raise ManifestHandoffRegistryUnavailable
        self._root = root
        self._attempts = attempt_lookup
        self._clearances = clearance_lookup
        self._artifacts = artifact_lookup
        self._codec = codec
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._preflight = preflight_id_generator or (lambda: secrets.token_hex(32))

    def __repr__(self) -> str:
        return "SafeLocalManifestHandoffSupervisorControlDirectoryCleanupPreflight()"

    def prepare_control_directory_cleanup(self, request):
        if type(request) is not PreflightManifestHandoffSupervisorControlDirectoryCleanup:
            raise ManifestHandoffRegistryUnavailable
        try:
            attempt = self._attempts(request.attempt_id)
            if attempt is None:
                return None
            if (
                type(attempt) is not CleanupManifestHandoffSupervisorControlDirectory
                or attempt.attempt_id != request.attempt_id
                or attempt.directory_id != request.directory_id
            ):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            clearance = self._clearances(attempt)
            if clearance is None:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if (
                type(clearance) is not ClearedManifestHandoffSupervisorControlDirectoryCleanup
                or clearance.request != attempt
                or clearance.retired.directory_id != request.directory_id
            ):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            artifacts = self._persistent_artifacts(clearance)
            return self._inspect(request, attempt, clearance, artifacts)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _inspect(self, request, attempt, clearance, artifacts):
        root = leaf = None
        try:
            root = self._open_root()
            name = clearance.retired.leaf.value
            try:
                leaf = os.open(name, _OPEN_DIRECTORY, dir_fd=root)
            except FileNotFoundError:
                if not self._same_root(root):
                    raise ManifestHandoffRegistryUnavailable
                current = self._clearances(attempt)
                if current != clearance:
                    return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
                return AbsentManifestHandoffSupervisorControlDirectoryCleanupPreflight(
                    request.attempt_id,
                    request.directory_id,
                    clearance.clearance_id,
                    self._now(clearance.cleared_at),
                )
            except OSError:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if not self._private_directory(leaf) or not self._same_entry(root, name, leaf):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            expected = {
                canonical_manifest_handoff_supervisor_control_artifact_name(role): record
                for role, record in artifacts.items()
            }
            if self._names(leaf) != set(expected):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            for filename, record in expected.items():
                if not self._matches_artifact(leaf, filename, record):
                    return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if self._names(leaf) != set(expected):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if not self._same_entry(root, name, leaf) or not self._same_root(root):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            current_clearance = self._clearances(attempt)
            current_artifacts = self._persistent_artifacts(clearance)
            if current_clearance != clearance or current_artifacts != artifacts:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            now = self._now(max(
                [clearance.cleared_at]
                + [record.published_at for record in artifacts.values()]
            ))
            return PreparedManifestHandoffSupervisorControlDirectoryCleanup(
                self._new_preflight_id(),
                request.attempt_id,
                request.directory_id,
                clearance.clearance_id,
                now,
            )
        finally:
            if leaf is not None:
                os.close(leaf)
            if root is not None:
                os.close(root)

    def _persistent_artifacts(self, clearance):
        result = {}
        for role in _ROLES:
            record = self._artifacts(clearance.retired.handle_id, role)
            if record is not None:
                if (
                    type(record) is not RecordedManifestHandoffSupervisorControlArtifact
                    or record.handle_id != clearance.retired.handle_id
                    or record.role is not role
                ):
                    raise ManifestHandoffRegistryUnavailable
                result[role] = record
        return result

    def _open_root(self):
        descriptor = None
        try:
            path_facts = os.lstat(self._root)
            if stat.S_ISLNK(path_facts.st_mode):
                raise ManifestHandoffRegistryUnavailable
            descriptor = os.open(self._root, _OPEN_DIRECTORY)
            facts = os.fstat(descriptor)
            if (
                not self._private_facts(facts)
                or path_facts.st_dev != facts.st_dev
                or path_facts.st_ino != facts.st_ino
            ):
                raise ManifestHandoffRegistryUnavailable
            return descriptor
        except ManifestHandoffRegistryUnavailable:
            if descriptor is not None:
                os.close(descriptor)
            raise
        except Exception:
            if descriptor is not None:
                os.close(descriptor)
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _private_facts(facts):
        return (
            stat.S_ISDIR(facts.st_mode)
            and facts.st_uid == os.geteuid()
            and stat.S_IMODE(facts.st_mode) == 0o700
        )

    @classmethod
    def _private_directory(cls, descriptor):
        return cls._private_facts(os.fstat(descriptor))

    def _same_root(self, descriptor):
        path_facts = os.lstat(self._root)
        current = os.fstat(descriptor)
        return (
            not stat.S_ISLNK(path_facts.st_mode)
            and path_facts.st_dev == current.st_dev
            and path_facts.st_ino == current.st_ino
        )

    @staticmethod
    def _same_entry(parent, name, descriptor):
        try:
            entry = os.stat(name, dir_fd=parent, follow_symlinks=False)
            current = os.fstat(descriptor)
            return (
                not stat.S_ISLNK(entry.st_mode)
                and entry.st_dev == current.st_dev
                and entry.st_ino == current.st_ino
            )
        except OSError:
            return False

    @staticmethod
    def _names(descriptor):
        names = os.listdir(descriptor)
        if any(type(name) is not str or not name or name in (".", "..") for name in names):
            raise ManifestHandoffRegistryUnavailable
        return set(names) if len(names) == len(set(names)) else set()

    def _matches_artifact(self, directory, name, record):
        descriptor = None
        try:
            before = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if stat.S_ISLNK(before.st_mode):
                return False
            descriptor = os.open(name, _OPEN_FILE, dir_fd=directory)
            opened = os.fstat(descriptor)
            if not self._private_file(opened) or not self._same_facts(before, opened):
                return False
            content = self._read_bounded(descriptor)
            after = os.stat(name, dir_fd=directory, follow_symlinks=False)
            final = os.fstat(descriptor)
            if not self._same_facts(opened, final) or not self._same_facts(final, after):
                return False
            document = self._codec.decode_content(content)
            encoded = self._codec.encode(document)
            return all((
                document.artifact_id == record.artifact_id,
                document.handle_id == record.handle_id,
                document.role is record.role,
                document.correlation_id == record.correlation_id,
                encoded.facts == record.facts,
                encoded.content.value == content,
            ))
        except OSError:
            return False
        finally:
            if descriptor is not None:
                os.close(descriptor)

    @staticmethod
    def _private_file(facts):
        return (
            stat.S_ISREG(facts.st_mode)
            and facts.st_uid == os.geteuid()
            and stat.S_IMODE(facts.st_mode) == 0o600
            and facts.st_nlink == 1
        )

    @staticmethod
    def _same_facts(left, right):
        return (
            left.st_dev == right.st_dev
            and left.st_ino == right.st_ino
            and left.st_mode == right.st_mode
            and left.st_uid == right.st_uid
            and left.st_nlink == right.st_nlink
            and left.st_size == right.st_size
            and left.st_mtime_ns == right.st_mtime_ns
            and left.st_ctime_ns == right.st_ctime_ns
        )

    @staticmethod
    def _read_bounded(descriptor):
        chunks = []
        remaining = _MAX_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if not content or len(content) > _MAX_BYTES:
            raise ManifestHandoffRegistryUnavailable
        return content

    def _new_preflight_id(self):
        try:
            return ManifestHandoffSupervisorControlDirectoryCleanupPreflightId(
                self._preflight()
            )
        except (TypeError, ValueError):
            raise ManifestHandoffRegistryUnavailable from None

    def _now(self, lower):
        now = self._clock()
        if (
            type(now) is not datetime
            or now.tzinfo is None
            or now.utcoffset() != timezone.utc.utcoffset(now)
            or now < lower
        ):
            raise ManifestHandoffRegistryUnavailable
        return now
