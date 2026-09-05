"""Peer-verified Engine API exchange on two already connected Unix streams."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import (
    AuthorizedManifestHandoffSupervisorEngineApiClientPeer,
    LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_daemon_peer import (
    AuthorizedManifestHandoffSupervisorEngineApiDaemonPeer,
    LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_exchange import (
    ClosedManifestHandoffSupervisorEngineApiExchange,
)


class VerifiedManifestHandoffSupervisorEngineApiExchange:
    """Resolve both kernel peers before invoking one closed exchange."""

    __slots__ = ("_client", "_daemon", "_exchange")

    def __init__(
        self,
        client_policy: LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy,
        daemon_policy: LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy,
        exchange: ClosedManifestHandoffSupervisorEngineApiExchange,
    ) -> None:
        if (
            type(client_policy) is not LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy
            or type(daemon_policy) is not LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy
            or type(exchange) is not ClosedManifestHandoffSupervisorEngineApiExchange
        ):
            raise ManifestHandoffRegistryUnavailable
        self._client = client_policy
        self._daemon = daemon_policy
        self._exchange = exchange

    def __repr__(self) -> str:
        return "VerifiedManifestHandoffSupervisorEngineApiExchange()"

    def exchange(self, client_stream, daemon_stream) -> None:
        try:
            if client_stream is daemon_stream:
                raise ManifestHandoffRegistryUnavailable
            client = self._client.authorize(client_stream)
            daemon = self._daemon.authorize(daemon_stream)
            self._require_bindings(client, daemon, client_stream, daemon_stream)
            self._exchange.exchange(client_stream, daemon_stream)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _require_bindings(client, daemon, client_stream, daemon_stream) -> None:
        if (
            type(client) is not AuthorizedManifestHandoffSupervisorEngineApiClientPeer
            or type(daemon) is not AuthorizedManifestHandoffSupervisorEngineApiDaemonPeer
            or client._stream is not client_stream
            or daemon._stream is not daemon_stream
            or client.descriptor == daemon.descriptor
            or client_stream.fileno() != client.descriptor
            or daemon_stream.fileno() != daemon.descriptor
        ):
            raise ManifestHandoffRegistryUnavailable
