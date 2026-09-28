"""Controlled lifecycle for the private local Engine API Unix listener."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import socket
import stat

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class ControlledManifestHandoffSupervisorEngineApiListener:
    """Publish and retire exactly one private listener without accepting clients."""

    __slots__ = (
        "_active", "_backlog", "_factory", "_gid", "_parent_gid",
        "_parent_uid", "_path", "_published", "_uid",
    )

    def __init__(
        self,
        *,
        socket_path: Path,
        proxy_uid: int,
        client_gid: int,
        parent_uid: int,
        parent_gid: int,
        backlog: int,
        socket_factory: Callable[[int, int], object] | None = None,
    ) -> None:
        if (
            not isinstance(socket_path, Path)
            or not socket_path.is_absolute()
            or socket_path == Path("/")
            or socket_path.parent == Path("/")
            or ".." in socket_path.parts
            or any(type(value) is not int or value < 1 for value in (
                proxy_uid, client_gid, parent_uid, parent_gid, backlog,
            ))
            or (socket_factory is not None and not callable(socket_factory))
        ):
            raise ManifestHandoffRegistryUnavailable
        self._path = socket_path
        self._uid, self._gid = proxy_uid, client_gid
        self._parent_uid, self._parent_gid = parent_uid, parent_gid
        self._backlog = backlog
        self._factory = socket_factory or socket.socket
        self._active = None
        self._published = None

    def __repr__(self) -> str:
        return "ControlledManifestHandoffSupervisorEngineApiListener()"

    def open(self):
        listener = None
        published = None
        try:
            if self._active is not None:
                raise ManifestHandoffRegistryUnavailable
            self._parent()
            try:
                os.lstat(self._path)
            except FileNotFoundError:
                pass
            else:
                raise ManifestHandoffRegistryUnavailable
            listener = self._factory(
                socket.AF_UNIX,
                socket.SOCK_STREAM | getattr(socket, "SOCK_CLOEXEC", 0),
            )
            listener.set_inheritable(False)
            listener.bind(str(self._path))
            published = os.lstat(self._path)
            if not stat.S_ISSOCK(published.st_mode):
                raise ManifestHandoffRegistryUnavailable
            os.chown(self._path, self._uid, self._gid, follow_symlinks=False)
            os.chmod(self._path, 0o660, follow_symlinks=False)
            listener.listen(self._backlog)
            self._verify(listener, published.st_dev, published.st_ino)
            self._active, self._published = listener, (
                published.st_dev, published.st_ino,
            )
            return listener
        except Exception:
            if listener is not None:
                try:
                    listener.close()
                except Exception:
                    pass
            if published is not None:
                self._remove_if_same(published.st_dev, published.st_ino)
            raise ManifestHandoffRegistryUnavailable from None

    def close(self, listener) -> None:
        if listener is not self._active or self._published is None:
            raise ManifestHandoffRegistryUnavailable
        try:
            listener.close()
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        device, inode = self._published
        self._active, self._published = None, None
        try:
            self._remove_if_same(device, inode, required=True)
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def _parent(self) -> None:
        facts = os.lstat(self._path.parent)
        if (
            not stat.S_ISDIR(facts.st_mode)
            or stat.S_ISLNK(facts.st_mode)
            or facts.st_uid != self._parent_uid
            or facts.st_gid != self._parent_gid
            or stat.S_IMODE(facts.st_mode) != 0o700
        ):
            raise ManifestHandoffRegistryUnavailable

    def _verify(self, listener, device, inode) -> None:
        descriptor = listener.fileno()
        path = os.lstat(self._path)
        current = os.fstat(descriptor)
        if (
            type(descriptor) is not int
            or descriptor < 0
            or not stat.S_ISSOCK(path.st_mode)
            or not stat.S_ISSOCK(current.st_mode)
            or path.st_dev != device
            or path.st_ino != inode
            or path.st_uid != self._uid
            or path.st_gid != self._gid
            or stat.S_IMODE(path.st_mode) != 0o660
            or os.get_inheritable(descriptor)
            or listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) != 1
            or listener.getsockname() != str(self._path)
        ):
            raise ManifestHandoffRegistryUnavailable

    def _remove_if_same(self, device, inode, *, required=False) -> None:
        try:
            facts = os.lstat(self._path)
            if (
                not stat.S_ISSOCK(facts.st_mode)
                or facts.st_dev != device
                or facts.st_ino != inode
            ):
                raise ManifestHandoffRegistryUnavailable
            os.unlink(self._path)
        except FileNotFoundError:
            if required:
                raise ManifestHandoffRegistryUnavailable from None
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
