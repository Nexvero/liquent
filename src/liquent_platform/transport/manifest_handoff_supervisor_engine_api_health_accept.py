"""Controlled one-client accept for the private Engine API health endpoint."""

from __future__ import annotations

from pathlib import Path

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_exchange import (
    VerifiedManifestHandoffSupervisorEngineApiHealthExchange,
)


class ControlledManifestHandoffSupervisorEngineApiHealthAccept:
    """Accept, configure, exchange and close exactly one health client."""

    __slots__ = ("_exchange", "_path", "_timeout")

    def __init__(self, *, socket_path: Path, client_timeout_seconds: float,
                 exchange: VerifiedManifestHandoffSupervisorEngineApiHealthExchange) -> None:
        if (
            not isinstance(socket_path, Path) or not socket_path.is_absolute()
            or socket_path == Path("/") or ".." in socket_path.parts
            or type(client_timeout_seconds) not in (int, float)
            or isinstance(client_timeout_seconds, bool) or client_timeout_seconds <= 0
            or type(exchange) is not VerifiedManifestHandoffSupervisorEngineApiHealthExchange
        ):
            raise ManifestHandoffRegistryUnavailable
        self._path = socket_path
        self._timeout = float(client_timeout_seconds)
        self._exchange = exchange

    def __repr__(self) -> str:
        return "ControlledManifestHandoffSupervisorEngineApiHealthAccept()"

    def serve_one(self, listener) -> None:
        client = None
        failed = False
        try:
            if listener.getsockname() != str(self._path):
                raise ManifestHandoffRegistryUnavailable
            accepted = listener.accept()
            if type(accepted) is not tuple or len(accepted) != 2:
                raise ManifestHandoffRegistryUnavailable
            client, address = accepted
            if client is None or address not in ("", None):
                raise ManifestHandoffRegistryUnavailable
            client.set_inheritable(False)
            client.settimeout(self._timeout)
            if (
                client.gettimeout() != self._timeout
                or client.getsockname() != str(self._path)
                or client.getpeername() not in ("", None)
            ):
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
