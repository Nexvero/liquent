"""Peer-verified one-message exchange for local Engine API proxy health."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import (
    AuthorizedManifestHandoffSupervisorEngineApiClientPeer,
    LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_protocol import (
    ClosedManifestHandoffSupervisorEngineApiHealthProtocol,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_stream_io import (
    BoundedManifestHandoffSupervisorEngineApiHealthStreamIo,
)


class VerifiedManifestHandoffSupervisorEngineApiHealthExchange:
    """Verify one accepted peer, then read, handle and write one message."""

    __slots__ = ("_io", "_peer", "_protocol")

    def __init__(
        self,
        peer_policy: LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy,
        protocol: ClosedManifestHandoffSupervisorEngineApiHealthProtocol,
        *,
        stream_io: BoundedManifestHandoffSupervisorEngineApiHealthStreamIo | None = None,
    ) -> None:
        stream_io = stream_io or BoundedManifestHandoffSupervisorEngineApiHealthStreamIo()
        if (
            type(peer_policy) is not LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy
            or type(protocol) is not ClosedManifestHandoffSupervisorEngineApiHealthProtocol
            or type(stream_io) is not BoundedManifestHandoffSupervisorEngineApiHealthStreamIo
        ):
            raise ManifestHandoffRegistryUnavailable
        self._peer = peer_policy
        self._protocol = protocol
        self._io = stream_io

    def __repr__(self) -> str:
        return "VerifiedManifestHandoffSupervisorEngineApiHealthExchange()"

    def exchange(self, stream) -> None:
        try:
            authorized = self._peer.authorize(stream)
            if (
                type(authorized) is not AuthorizedManifestHandoffSupervisorEngineApiClientPeer
                or authorized._stream is not stream
                or stream.fileno() != authorized.descriptor
            ):
                raise ManifestHandoffRegistryUnavailable
            request = self._io.read_request(stream)
            response = self._protocol.handle(request)
            if type(response) is not bytes or not response:
                raise ManifestHandoffRegistryUnavailable
            if stream.fileno() != authorized.descriptor:
                raise ManifestHandoffRegistryUnavailable
            self._io.write_response(stream, response)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
