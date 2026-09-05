"""Safe local filesystem boundary for supervisor control directories."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import stat

from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    ActiveManifestHandoffSupervisorControlDirectory,
    ManifestHandoffSupervisorControlDirectoryConflict,
    ManifestHandoffSupervisorControlDirectoryLifecycle,
    ReservedManifestHandoffSupervisorControlDirectory,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.persistence.identity_errors import (
    ManifestHandoffRegistryUnavailable,
)


class SafeLocalManifestHandoffSupervisorControlDirectories:
    """Create reserved leaves and resolve only current active bindings."""

    __slots__ = ("_root", "_lookup")

    def __init__(
        self,
        root: Path,
        *,
        lookup: Callable[
            [ManifestHandoffSupervisorControlDirectoryId],
            ManifestHandoffSupervisorControlDirectoryLifecycle | None,
        ],
    ) -> None:
        if not isinstance(root, Path) or not root.is_absolute() or not callable(lookup):
            raise ManifestHandoffRegistryUnavailable
        self._root = root
        self._lookup = lookup

    def __repr__(self) -> str:
        return "SafeLocalManifestHandoffSupervisorControlDirectories()"

    def create_reserved(
        self, reservation: ReservedManifestHandoffSupervisorControlDirectory
    ) -> Path | ManifestHandoffSupervisorControlDirectoryConflict:
        if type(reservation) is not ReservedManifestHandoffSupervisorControlDirectory:
            raise ManifestHandoffRegistryUnavailable
        root = child = None
        created = False
        try:
            root = self._open_root()
            leaf = reservation.leaf.value
            try:
                os.mkdir(leaf, 0o700, dir_fd=root)
                created = True
            except FileExistsError:
                pass
            try:
                child = os.open(
                    leaf,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=root,
                )
            except OSError:
                return ManifestHandoffSupervisorControlDirectoryConflict()
            if not self._private_directory(child):
                return ManifestHandoffSupervisorControlDirectoryConflict()
            if not self._same_entry(root, leaf, child):
                return ManifestHandoffSupervisorControlDirectoryConflict()
            if created:
                os.fsync(child)
                os.fsync(root)
            if not self._same_root(root):
                raise ManifestHandoffRegistryUnavailable
            return self._root / leaf
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if child is not None:
                os.close(child)
            if root is not None:
                os.close(root)

    def resolve_active(
        self, directory_id: ManifestHandoffSupervisorControlDirectoryId
    ) -> Path | None:
        if type(directory_id) is not ManifestHandoffSupervisorControlDirectoryId:
            raise ManifestHandoffRegistryUnavailable
        try:
            lifecycle = self._lookup(directory_id)
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        if lifecycle is None:
            return None
        if type(lifecycle) is not ActiveManifestHandoffSupervisorControlDirectory:
            return None
        root = child = None
        try:
            root = self._open_root()
            leaf = lifecycle.leaf.value
            try:
                child = os.open(
                    leaf,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=root,
                )
            except FileNotFoundError:
                raise ManifestHandoffRegistryUnavailable from None
            if not self._private_directory(child):
                raise ManifestHandoffRegistryUnavailable
            if not self._same_entry(root, leaf, child):
                raise ManifestHandoffRegistryUnavailable
            if not self._same_root(root):
                raise ManifestHandoffRegistryUnavailable
            return self._root / leaf
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if child is not None:
                os.close(child)
            if root is not None:
                os.close(root)

    def _open_root(self) -> int:
        descriptor = None
        try:
            path_facts = os.lstat(self._root)
            if stat.S_ISLNK(path_facts.st_mode):
                raise ManifestHandoffRegistryUnavailable
            descriptor = os.open(
                self._root,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            descriptor_facts = os.fstat(descriptor)
            if (
                not self._private_facts(descriptor_facts)
                or path_facts.st_dev != descriptor_facts.st_dev
                or path_facts.st_ino != descriptor_facts.st_ino
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
    def _private_facts(facts: os.stat_result) -> bool:
        return (
            stat.S_ISDIR(facts.st_mode)
            and facts.st_uid == os.geteuid()
            and stat.S_IMODE(facts.st_mode) == 0o700
        )

    @classmethod
    def _private_directory(cls, descriptor: int) -> bool:
        return cls._private_facts(os.fstat(descriptor))

    def _same_root(self, root: int) -> bool:
        path_facts = os.lstat(self._root)
        root_facts = os.fstat(root)
        return (
            not stat.S_ISLNK(path_facts.st_mode)
            and path_facts.st_dev == root_facts.st_dev
            and path_facts.st_ino == root_facts.st_ino
        )

    @staticmethod
    def _same_entry(root: int, leaf: str, child: int) -> bool:
        path_facts = os.stat(leaf, dir_fd=root, follow_symlinks=False)
        child_facts = os.fstat(child)
        return not (
            path_facts.st_dev != child_facts.st_dev
            or path_facts.st_ino != child_facts.st_ino
        )
