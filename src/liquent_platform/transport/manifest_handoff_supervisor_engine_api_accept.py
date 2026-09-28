"""Controlled one-client accept operation for the private Engine API listener."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import socket
import stat

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_connected_exchange import (
    ConnectedManifestHandoffSupervisorEngineApiExchange,
)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiAcceptPollResult:
    served: bool


class ControlledManifestHandoffSupervisorEngineApiAccept:
    """Accept, configure, serve and close exactly one client stream."""

    __slots__ = ("_exchange", "_path", "_timeout")

    def __init__(
        self,
        *,
        socket_path: Path,
        client_timeout_seconds: float,
        exchange: ConnectedManifestHandoffSupervisorEngineApiExchange,
    ) -> None:
        if (
            not isinstance(socket_path, Path)
            or not socket_path.is_absolute()
            or socket_path == Path("/")
            or ".." in socket_path.parts
            or type(client_timeout_seconds) not in (int, float)
            or isinstance(client_timeout_seconds, bool)
            or client_timeout_seconds <= 0
            or type(exchange) is not ConnectedManifestHandoffSupervisorEngineApiExchange
        ):
            raise ManifestHandoffRegistryUnavailable
        self._path = socket_path
        self._timeout = float(client_timeout_seconds)
        self._exchange = exchange

    def __repr__(self) -> str:
        return "ControlledManifestHandoffSupervisorEngineApiAccept()"

    def serve_one(self, listener) -> None:
        self._serve_one(listener, timeout_is_neutral=False)

    def poll_one(self, listener) -> ManifestHandoffSupervisorEngineApiAcceptPollResult:
        return self._serve_one(listener, timeout_is_neutral=True)

    def _serve_one(
        self, listener, *, timeout_is_neutral: bool,
    ) -> ManifestHandoffSupervisorEngineApiAcceptPollResult:
        client = None
        failed = False
        timed_out = False
        try:
            self._listener(listener)
            try:
                accepted = listener.accept()
            except socket.timeout:
                if not timeout_is_neutral:
                    raise
                timed_out = True
                accepted = None
            if timed_out:
                return ManifestHandoffSupervisorEngineApiAcceptPollResult(False)
            if type(accepted) is not tuple or len(accepted) != 2:
                raise ManifestHandoffRegistryUnavailable
            client, address = accepted
            if client is None or address not in ("", None):
                raise ManifestHandoffRegistryUnavailable
            client.set_inheritable(False)
            client.settimeout(self._timeout)
            self._client(client)
            self._exchange.serve(client)
        except Exception:
            failed = True
        close_failed = False
        if client is not None:
            try:
                client.close()
            except Exception:
                close_failed = True
        if failed or close_failed:
            raise ManifestHandoffRegistryUnavailable from None
        return ManifestHandoffSupervisorEngineApiAcceptPollResult(True)

    def _listener(self, listener) -> None:
        if (
            listener is None
            or listener.family != socket.AF_UNIX
            or (listener.type & socket.SOCK_STREAM) != socket.SOCK_STREAM
            or listener.getsockname() != str(self._path)
            or listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) != 1
        ):
            raise ManifestHandoffRegistryUnavailable
        descriptor = listener.fileno()
        facts = os.fstat(descriptor)
        if (
            type(descriptor) is not int
            or descriptor < 0
            or not stat.S_ISSOCK(facts.st_mode)
            or os.get_inheritable(descriptor)
        ):
            raise ManifestHandoffRegistryUnavailable

    def _client(self, client) -> None:
        descriptor = client.fileno()
        facts = os.fstat(descriptor)
        if (
            client.family != socket.AF_UNIX
            or (client.type & socket.SOCK_STREAM) != socket.SOCK_STREAM
            or type(descriptor) is not int
            or descriptor < 0
            or not stat.S_ISSOCK(facts.st_mode)
            or os.get_inheritable(descriptor)
            or client.gettimeout() != self._timeout
            or client.getsockname() != str(self._path)
            or client.getpeername() not in ("", None)
            or client.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) != 0
        ):
            raise ManifestHandoffRegistryUnavailable
