"""Linux descriptor and peer policy for a connected Engine API daemon socket."""

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
class AuthorizedManifestHandoffSupervisorEngineApiDaemonPeer:
    descriptor: int
    process_id: int
    user_id: int
    group_id: int
    daemon_socket: Path
    _stream: object = field(repr=False, compare=False)


class LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy:
    """Authorize current kernel facts for one connected daemon Unix stream."""

    __slots__ = ("_gid", "_socket", "_timeout", "_uid")

    def __init__(
        self,
        *,
        daemon_socket: Path,
        daemon_uid: int,
        daemon_gid: int,
        timeout_seconds: float,
    ) -> None:
        if (
            not isinstance(daemon_socket, Path)
            or not daemon_socket.is_absolute()
            or daemon_socket == Path("/")
            or ".." in daemon_socket.parts
            or type(daemon_uid) is not int
            or daemon_uid < 0
            or type(daemon_gid) is not int
            or daemon_gid < 1
            or type(timeout_seconds) not in (int, float)
            or isinstance(timeout_seconds, bool)
            or timeout_seconds <= 0
        ):
            raise ManifestHandoffRegistryUnavailable
        self._socket = daemon_socket
        self._uid = daemon_uid
        self._gid = daemon_gid
        self._timeout = float(timeout_seconds)

    def authorize(
        self, daemon_stream
    ) -> AuthorizedManifestHandoffSupervisorEngineApiDaemonPeer:
        try:
            if (
                daemon_stream is None
                or daemon_stream.family != socket.AF_UNIX
                or (daemon_stream.type & socket.SOCK_STREAM) != socket.SOCK_STREAM
                or daemon_stream.gettimeout() != self._timeout
            ):
                raise ManifestHandoffRegistryUnavailable
            descriptor = daemon_stream.fileno()
            if type(descriptor) is not int or descriptor < 0:
                raise ManifestHandoffRegistryUnavailable
            before = os.fstat(descriptor)
            if (
                not stat.S_ISSOCK(before.st_mode)
                or os.get_inheritable(descriptor)
                or daemon_stream.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) != 0
                or daemon_stream.getsockname() != ""
                or daemon_stream.getpeername() != str(self._socket)
            ):
                raise ManifestHandoffRegistryUnavailable
            process_id, user_id, group_id = self._credentials(daemon_stream)
            after = os.fstat(descriptor)
            if (
                daemon_stream.fileno() != descriptor
                or daemon_stream.getsockname() != ""
                or daemon_stream.getpeername() != str(self._socket)
                or before.st_dev != after.st_dev
                or before.st_ino != after.st_ino
                or before.st_mode != after.st_mode
                or process_id < 1
                or user_id != self._uid
                or group_id != self._gid
            ):
                raise ManifestHandoffRegistryUnavailable
            return AuthorizedManifestHandoffSupervisorEngineApiDaemonPeer(
                descriptor, process_id, user_id, group_id, self._socket,
                daemon_stream,
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _credentials(daemon_stream) -> tuple[int, int, int]:
        raw = daemon_stream.getsockopt(
            socket.SOL_SOCKET, _SO_PEERCRED, struct.calcsize("3i")
        )
        if type(raw) is not bytes or len(raw) != struct.calcsize("3i"):
            raise ManifestHandoffRegistryUnavailable
        return struct.unpack("3i", raw)
