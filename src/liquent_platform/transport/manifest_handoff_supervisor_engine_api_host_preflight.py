"""Read-only host facts for the future local supervisor Engine API proxy."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from liquent_platform.application.health import Readiness
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class ManifestHandoffSupervisorEngineApiHostPreflight:
    """Check exact socket and root facts without mutation or connection."""

    __slots__ = (
        "_client_gid", "_control", "_daemon_gid", "_daemon_socket",
        "_daemon_uid", "_data_gid", "_data_uid", "_host_gid", "_host_uid",
        "_proxy_socket", "_proxy_uid", "_source", "_target",
    )

    def __init__(
        self, *, proxy_socket: Path, daemon_socket: Path,
        control_root: Path, source_root: Path, target_root: Path,
        proxy_uid: int, client_gid: int, daemon_uid: int, daemon_gid: int,
        host_owner_uid: int, host_owner_gid: int,
        data_owner_uid: int, data_gid: int,
    ) -> None:
        paths = (proxy_socket, daemon_socket, control_root, source_root, target_root)
        positive = (
            proxy_uid, client_gid, daemon_gid, host_owner_uid, host_owner_gid,
            data_owner_uid, data_gid,
        )
        if (
            any(not isinstance(path, Path) or not path.is_absolute()
                or path == Path("/") or ".." in path.parts for path in paths)
            or len(set(paths)) != len(paths)
            or any(type(value) is not int or value < 1 for value in positive)
            or type(daemon_uid) is not int or daemon_uid < 0
        ):
            raise ManifestHandoffRegistryUnavailable
        self._proxy_socket, self._daemon_socket = proxy_socket, daemon_socket
        self._control, self._source, self._target = (
            control_root, source_root, target_root
        )
        self._proxy_uid, self._client_gid = proxy_uid, client_gid
        self._daemon_uid, self._daemon_gid = daemon_uid, daemon_gid
        self._host_uid, self._host_gid = host_owner_uid, host_owner_gid
        self._data_uid, self._data_gid = data_owner_uid, data_gid

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiHostPreflight()"

    def check(self) -> Readiness:
        return self._check(include_proxy=True)

    def check_before_listener(self) -> Readiness:
        """Check every host dependency that must pre-exist listener publication."""
        return self._check(include_proxy=False)

    def _check(self, *, include_proxy: bool) -> Readiness:
        try:
            if include_proxy:
                self._socket(
                    self._proxy_socket, self._proxy_uid, self._client_gid, 0o660
                )
            self._socket(
                self._daemon_socket, self._daemon_uid, self._daemon_gid, 0o660
            )
            self._directory(
                self._control, self._host_uid, self._host_gid, 0o700
            )
            self._directory(
                self._source, self._data_uid, self._data_gid, 0o750
            )
            self._directory(
                self._target, self._data_uid, self._data_gid, 0o750
            )
            reason = (
                "manifest_handoff_supervisor_host_ready"
                if include_proxy
                else "manifest_handoff_supervisor_host_dependencies_ready"
            )
            return Readiness(True, reason)
        except Exception:
            return Readiness(False, "manifest_handoff_supervisor_host_unavailable")

    @staticmethod
    def _socket(path: Path, uid: int, gid: int, mode: int) -> None:
        before = os.lstat(path)
        if (
            not stat.S_ISSOCK(before.st_mode)
            or before.st_uid != uid
            or before.st_gid != gid
            or stat.S_IMODE(before.st_mode) != mode
        ):
            raise ManifestHandoffRegistryUnavailable
        after = os.lstat(path)
        if (
            before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
            or before.st_mode != after.st_mode
            or before.st_uid != after.st_uid
            or before.st_gid != after.st_gid
        ):
            raise ManifestHandoffRegistryUnavailable

    @staticmethod
    def _directory(path: Path, uid: int, gid: int, mode: int) -> None:
        descriptor = None
        try:
            before = os.lstat(path)
            if stat.S_ISLNK(before.st_mode):
                raise ManifestHandoffRegistryUnavailable
            descriptor = os.open(
                path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            )
            current = os.fstat(descriptor)
            after = os.lstat(path)
            if not all((
                stat.S_ISDIR(current.st_mode),
                current.st_uid == uid,
                current.st_gid == gid,
                stat.S_IMODE(current.st_mode) == mode,
                before.st_dev == current.st_dev == after.st_dev,
                before.st_ino == current.st_ino == after.st_ino,
                not stat.S_ISLNK(after.st_mode),
            )):
                raise ManifestHandoffRegistryUnavailable
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
