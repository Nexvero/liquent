"""One-shot local physical removal of a claimed supervisor control directory."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import os
from pathlib import Path
import stat

from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    RetiredManifestHandoffSupervisorControlDirectory,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryCleanupConflict,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_execution import (
    ClaimedManifestHandoffSupervisorControlDirectoryCleanup,
    RemovedManifestHandoffSupervisorControlDirectory,
    UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect,
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


class SafeLocalManifestHandoffSupervisorControlDirectoryPhysicalCleanup:
    """Remove only a fully revalidated claimed leaf, once and non-recursively."""

    __slots__ = ("_root", "_claims", "_directories", "_artifacts", "_codec", "_clock")

    def __init__(
        self,
        root: Path,
        *,
        claim_lookup: Callable,
        directory_lookup: Callable,
        artifact_lookup: Callable,
        codec: CanonicalManifestHandoffSupervisorControlArtifactCodec,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if (
            not isinstance(root, Path)
            or not root.is_absolute()
            or not callable(claim_lookup)
            or not callable(directory_lookup)
            or not callable(artifact_lookup)
            or type(codec) is not CanonicalManifestHandoffSupervisorControlArtifactCodec
            or (clock is not None and not callable(clock))
        ):
            raise ManifestHandoffRegistryUnavailable
        self._root = root
        self._claims = claim_lookup
        self._directories = directory_lookup
        self._artifacts = artifact_lookup
        self._codec = codec
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "SafeLocalManifestHandoffSupervisorControlDirectoryPhysicalCleanup()"

    def remove_control_directory(self, claimed):
        if type(claimed) is not ClaimedManifestHandoffSupervisorControlDirectoryCleanup:
            raise ManifestHandoffRegistryUnavailable
        root = leaf = None
        effect_started = False
        try:
            current, retired, artifacts = self._current(claimed)
            if current is None:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            root = self._open_root()
            leaf_name = retired.leaf.value
            try:
                leaf = os.open(leaf_name, _OPEN_DIRECTORY, dir_fd=root)
            except OSError:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if not self._safe_leaf(root, leaf_name, leaf):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            remaining = {
                canonical_manifest_handoff_supervisor_control_artifact_name(role): record
                for role, record in artifacts.items()
            }
            if not self._inventory(root, leaf_name, leaf, remaining):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            for role in _ROLES:
                filename = canonical_manifest_handoff_supervisor_control_artifact_name(role)
                if filename not in remaining:
                    continue
                if not self._current_matches(claimed, retired, artifacts):
                    return self._uncertain(claimed, effect_started)
                if not self._inventory(root, leaf_name, leaf, remaining):
                    return self._uncertain(claimed, effect_started)
                if not self._matches_artifact(leaf, filename, remaining[filename]):
                    return self._uncertain(claimed, effect_started)
                effect_started = True
                os.unlink(filename, dir_fd=leaf)
                os.fsync(leaf)
                del remaining[filename]
            if not self._current_matches(claimed, retired, artifacts):
                return self._uncertain(claimed, effect_started)
            if remaining or self._names(leaf) or not self._safe_leaf(root, leaf_name, leaf):
                return self._uncertain(claimed, effect_started)
            effect_started = True
            os.rmdir(leaf_name, dir_fd=root)
            os.fsync(root)
            try:
                os.stat(leaf_name, dir_fd=root, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                return self._uncertain(claimed, True)
            if not self._same_root(root):
                return self._uncertain(claimed, True)
            removed_at = self._now(claimed.claimed_at)
            return RemovedManifestHandoffSupervisorControlDirectory(
                claimed.claim_id,
                claimed.attempt_id,
                claimed.directory_id,
                removed_at,
            )
        except Exception:
            if effect_started:
                return self._unknown(claimed)
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if leaf is not None:
                self._close(leaf)
            if root is not None:
                self._close(root)

    def _current(self, claimed):
        current = self._claims(claimed.attempt_id)
        if current is None:
            return None, None, None
        if type(current) is not ClaimedManifestHandoffSupervisorControlDirectoryCleanup:
            return None, None, None
        if current != claimed:
            return None, None, None
        retired = self._directories(claimed.directory_id)
        if type(retired) is not RetiredManifestHandoffSupervisorControlDirectory:
            return None, None, None
        if retired.directory_id != claimed.directory_id:
            return None, None, None
        artifacts = self._persistent_artifacts(retired)
        return current, retired, artifacts

    def _current_matches(self, claimed, retired, artifacts):
        current, current_retired, current_artifacts = self._current(claimed)
        return (
            current == claimed
            and current_retired == retired
            and current_artifacts == artifacts
        )

    def _persistent_artifacts(self, retired):
        result = {}
        for role in _ROLES:
            record = self._artifacts(retired.handle_id, role)
            if record is not None:
                if (
                    type(record) is not RecordedManifestHandoffSupervisorControlArtifact
                    or record.handle_id != retired.handle_id
                    or record.role is not role
                ):
                    raise ManifestHandoffRegistryUnavailable
                result[role] = record
        return result

    def _inventory(self, root, leaf_name, leaf, expected):
        if not self._same_root(root) or not self._safe_leaf(root, leaf_name, leaf):
            return False
        if self._names(leaf) != set(expected):
            return False
        return all(
            self._matches_artifact(leaf, filename, record)
            for filename, record in expected.items()
        )

    def _open_root(self):
        descriptor = None
        try:
            path_facts = os.lstat(self._root)
            if stat.S_ISLNK(path_facts.st_mode):
                raise ManifestHandoffRegistryUnavailable
            descriptor = os.open(self._root, _OPEN_DIRECTORY)
            facts = os.fstat(descriptor)
            if (
                not self._private_directory_facts(facts)
                or path_facts.st_dev != facts.st_dev
                or path_facts.st_ino != facts.st_ino
            ):
                raise ManifestHandoffRegistryUnavailable
            return descriptor
        except Exception:
            if descriptor is not None:
                os.close(descriptor)
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _private_directory_facts(facts):
        return (
            stat.S_ISDIR(facts.st_mode)
            and facts.st_uid == os.geteuid()
            and stat.S_IMODE(facts.st_mode) == 0o700
        )

    def _same_root(self, root):
        try:
            path_facts = os.lstat(self._root)
            facts = os.fstat(root)
            return (
                not stat.S_ISLNK(path_facts.st_mode)
                and path_facts.st_dev == facts.st_dev
                and path_facts.st_ino == facts.st_ino
                and self._private_directory_facts(facts)
            )
        except OSError:
            return False

    def _safe_leaf(self, root, name, leaf):
        try:
            entry = os.stat(name, dir_fd=root, follow_symlinks=False)
            facts = os.fstat(leaf)
            return (
                not stat.S_ISLNK(entry.st_mode)
                and self._private_directory_facts(facts)
                and entry.st_dev == facts.st_dev
                and entry.st_ino == facts.st_ino
            )
        except OSError:
            return False

    @staticmethod
    def _names(leaf):
        names = os.listdir(leaf)
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
                self._close(descriptor)

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
        return all((
            left.st_dev == right.st_dev,
            left.st_ino == right.st_ino,
            left.st_mode == right.st_mode,
            left.st_uid == right.st_uid,
            left.st_nlink == right.st_nlink,
            left.st_size == right.st_size,
            left.st_mtime_ns == right.st_mtime_ns,
            left.st_ctime_ns == right.st_ctime_ns,
        ))

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

    @staticmethod
    def _unknown(claimed):
        return UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect(
            claimed.claim_id, claimed.attempt_id, claimed.directory_id
        )

    @staticmethod
    def _close(descriptor):
        try:
            os.close(descriptor)
        except OSError:
            pass

    def _uncertain(self, claimed, effect_started):
        if effect_started:
            return self._unknown(claimed)
        return ManifestHandoffSupervisorControlDirectoryCleanupConflict()

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
