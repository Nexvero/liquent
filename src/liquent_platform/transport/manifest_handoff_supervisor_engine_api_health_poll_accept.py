"""Bounded polling accept for the private Engine API health endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import socket

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_exchange import VerifiedManifestHandoffSupervisorEngineApiHealthExchange


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiHealthPollResult:
    served: bool


class BoundedManifestHandoffSupervisorEngineApiHealthPollAccept:
    __slots__ = ("_client_timeout", "_exchange", "_path", "_poll_timeout")

    def __init__(self, *, socket_path: Path, poll_timeout_seconds: float,
                 client_timeout_seconds: float,
                 exchange: VerifiedManifestHandoffSupervisorEngineApiHealthExchange) -> None:
        numbers = (poll_timeout_seconds, client_timeout_seconds)
        if (not isinstance(socket_path, Path) or not socket_path.is_absolute()
                or socket_path == Path("/") or ".." in socket_path.parts
                or any(type(value) not in (int, float) or isinstance(value, bool)
                       or value <= 0 for value in numbers)
                or type(exchange) is not VerifiedManifestHandoffSupervisorEngineApiHealthExchange):
            raise ManifestHandoffRegistryUnavailable
        self._path = socket_path
        self._poll_timeout = float(poll_timeout_seconds)
        self._client_timeout = float(client_timeout_seconds)
        self._exchange = exchange

    def __repr__(self) -> str:
        return "BoundedManifestHandoffSupervisorEngineApiHealthPollAccept()"

    def poll_one(self, listener) -> ManifestHandoffSupervisorEngineApiHealthPollResult:
        client = None
        failed = False
        try:
            if (listener.getsockname() != str(self._path)
                    or listener.gettimeout() != self._poll_timeout):
                raise ManifestHandoffRegistryUnavailable
            try:
                accepted = listener.accept()
            except socket.timeout:
                return ManifestHandoffSupervisorEngineApiHealthPollResult(False)
            if type(accepted) is not tuple or len(accepted) != 2:
                raise ManifestHandoffRegistryUnavailable
            client, address = accepted
            if client is None or address not in ("", None):
                raise ManifestHandoffRegistryUnavailable
            client.set_inheritable(False)
            client.settimeout(self._client_timeout)
            if (client.gettimeout() != self._client_timeout
                    or client.getsockname() != str(self._path)
                    or client.getpeername() not in ("", None)):
                raise ManifestHandoffRegistryUnavailable
            self._exchange.exchange(client)
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
        return ManifestHandoffSupervisorEngineApiHealthPollResult(True)
