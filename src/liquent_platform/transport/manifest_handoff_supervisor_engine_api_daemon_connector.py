"""Controlled one-shot Unix connection to the local Engine API daemon."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import socket
import stat

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class ControlledManifestHandoffSupervisorEngineApiDaemonConnector:
    """Create one bounded daemon stream and transfer ownership on success."""

    __slots__ = ("_factory", "_socket", "_timeout")

    def __init__(
        self,
        *,
        daemon_socket: Path,
        timeout_seconds: float,
        socket_factory: Callable[[int, int], object] | None = None,
    ) -> None:
        if (
            not isinstance(daemon_socket, Path)
            or not daemon_socket.is_absolute()
            or daemon_socket == Path("/")
            or ".." in daemon_socket.parts
            or type(timeout_seconds) not in (int, float)
            or isinstance(timeout_seconds, bool)
            or timeout_seconds <= 0
            or (socket_factory is not None and not callable(socket_factory))
        ):
            raise ManifestHandoffRegistryUnavailable
        self._socket = daemon_socket
        self._timeout = float(timeout_seconds)
        self._factory = socket_factory or socket.socket

    def __repr__(self) -> str:
        return "ControlledManifestHandoffSupervisorEngineApiDaemonConnector()"

    def connect(self):
        stream = None
        try:
            stream = self._factory(
                socket.AF_UNIX,
                socket.SOCK_STREAM | getattr(socket, "SOCK_CLOEXEC", 0),
            )
            if stream is None:
                raise ManifestHandoffRegistryUnavailable
            stream.set_inheritable(False)
            stream.settimeout(self._timeout)
            stream.connect(str(self._socket))
            descriptor = stream.fileno()
            facts = os.fstat(descriptor)
            if (
                stream.family != socket.AF_UNIX
                or (stream.type & socket.SOCK_STREAM) != socket.SOCK_STREAM
                or type(descriptor) is not int
                or descriptor < 0
                or not stat.S_ISSOCK(facts.st_mode)
                or os.get_inheritable(descriptor)
                or stream.gettimeout() != self._timeout
                or stream.getsockname() != ""
                or stream.getpeername() != str(self._socket)
            ):
                raise ManifestHandoffRegistryUnavailable
            return stream
        except Exception:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass
            raise ManifestHandoffRegistryUnavailable from None
