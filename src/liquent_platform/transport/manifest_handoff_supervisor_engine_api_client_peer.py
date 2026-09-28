"""Linux peer and descriptor policy for an accepted Engine API client socket."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import socket
import stat
import struct

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_SO_PEERCRED = getattr(socket, "SO_PEERCRED", 17)


@dataclass(frozen=True, slots=True)
class AuthorizedManifestHandoffSupervisorEngineApiClientPeer:
    descriptor: int
    process_id: int
    user_id: int
    group_id: int
    local_socket: Path
    _stream: object = field(repr=False, compare=False)


class LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy:
    """Authorize current kernel facts for one already accepted Unix stream."""

    __slots__ = ("_gid", "_socket", "_timeout", "_uid")

    def __init__(
        self,
        *,
        local_socket: Path,
        client_uid: int,
        client_gid: int,
        timeout_seconds: float,
    ) -> None:
        if (
            not isinstance(local_socket, Path)
            or not local_socket.is_absolute()
            or local_socket == Path("/")
            or ".." in local_socket.parts
            or type(client_uid) is not int
            or client_uid < 1
            or type(client_gid) is not int
            or client_gid < 1
            or type(timeout_seconds) not in (int, float)
            or isinstance(timeout_seconds, bool)
            or timeout_seconds <= 0
        ):
            raise ManifestHandoffRegistryUnavailable
        self._socket = local_socket
        self._uid = client_uid
        self._gid = client_gid
        self._timeout = float(timeout_seconds)

    def authorize(
        self, client_socket
    ) -> AuthorizedManifestHandoffSupervisorEngineApiClientPeer:
        try:
            if (
                client_socket is None
                or client_socket.family != socket.AF_UNIX
                or (client_socket.type & socket.SOCK_STREAM) != socket.SOCK_STREAM
                or client_socket.gettimeout() != self._timeout
            ):
                raise ManifestHandoffRegistryUnavailable
            descriptor = client_socket.fileno()
            if type(descriptor) is not int or descriptor < 0:
                raise ManifestHandoffRegistryUnavailable
            before = os.fstat(descriptor)
            if (
                not stat.S_ISSOCK(before.st_mode)
                or os.get_inheritable(descriptor)
                or client_socket.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) != 0
                or client_socket.getsockname() != str(self._socket)
            ):
                raise ManifestHandoffRegistryUnavailable
            peer_name = client_socket.getpeername()
            if peer_name not in ("", None) and type(peer_name) is not str:
                raise ManifestHandoffRegistryUnavailable
            process_id, user_id, group_id = self._credentials(client_socket)
            after = os.fstat(descriptor)
            if (
                client_socket.fileno() != descriptor
                or client_socket.getsockname() != str(self._socket)
                or before.st_dev != after.st_dev
                or before.st_ino != after.st_ino
                or before.st_mode != after.st_mode
                or process_id < 1
                or user_id != self._uid
                or group_id != self._gid
            ):
                raise ManifestHandoffRegistryUnavailable
            return AuthorizedManifestHandoffSupervisorEngineApiClientPeer(
                descriptor, process_id, user_id, group_id, self._socket,
                client_socket,
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _credentials(client_socket) -> tuple[int, int, int]:
        raw = client_socket.getsockopt(
            socket.SOL_SOCKET, _SO_PEERCRED, struct.calcsize("3i")
        )
        if type(raw) is not bytes or len(raw) != struct.calcsize("3i"):
            raise ManifestHandoffRegistryUnavailable
        values = struct.unpack("3i", raw)
        if any(type(value) is not int for value in values):
            raise ManifestHandoffRegistryUnavailable
        return values
