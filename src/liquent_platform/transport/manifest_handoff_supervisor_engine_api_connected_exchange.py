"""Connect, verify, exchange and close one Engine API daemon stream."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_connector import (
    ControlledManifestHandoffSupervisorEngineApiDaemonConnector,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_verified_exchange import (
    VerifiedManifestHandoffSupervisorEngineApiExchange,
)


class ConnectedManifestHandoffSupervisorEngineApiExchange:
    """Own exactly one daemon stream for exactly one verified exchange."""

    __slots__ = ("_connector", "_exchange")

    def __init__(
        self,
        connector: ControlledManifestHandoffSupervisorEngineApiDaemonConnector,
        exchange: VerifiedManifestHandoffSupervisorEngineApiExchange,
    ) -> None:
        if (
            type(connector) is not ControlledManifestHandoffSupervisorEngineApiDaemonConnector
            or type(exchange) is not VerifiedManifestHandoffSupervisorEngineApiExchange
        ):
            raise ManifestHandoffRegistryUnavailable
        self._connector = connector
        self._exchange = exchange

    def __repr__(self) -> str:
        return "ConnectedManifestHandoffSupervisorEngineApiExchange()"

    def serve(self, client_stream) -> None:
        daemon_stream = None
        failed = False
        try:
            daemon_stream = self._connector.connect()
            self._exchange.exchange(client_stream, daemon_stream)
        except Exception:
            failed = True
        close_failed = False
        if daemon_stream is not None:
            try:
                daemon_stream.close()
            except Exception:
                close_failed = True
        if failed or close_failed:
            raise ManifestHandoffRegistryUnavailable from None
