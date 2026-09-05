"""Closed one-request Engine API exchange on two connected streams."""

from __future__ import annotations

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_gate import (
    ClosedManifestHandoffSupervisorEngineApiGate,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_response_policy import (
    AuthorizedManifestHandoffSupervisorEngineApiResponse,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_stream_io import (
    BoundedManifestHandoffSupervisorEngineApiStreamIo,
)


_REASONS = {
    200: "OK",
    201: "Created",
    204: "No Content",
    304: "Not Modified",
    404: "Not Found",
}


class ClosedManifestHandoffSupervisorEngineApiExchange:
    """Run one gate-bound exchange without acquiring or closing either stream."""

    __slots__ = ("_gate", "_io")

    def __init__(
        self,
        gate: ClosedManifestHandoffSupervisorEngineApiGate,
        *,
        stream_io: BoundedManifestHandoffSupervisorEngineApiStreamIo | None = None,
    ) -> None:
        stream_io = stream_io or BoundedManifestHandoffSupervisorEngineApiStreamIo()
        if (
            type(gate) is not ClosedManifestHandoffSupervisorEngineApiGate
            or type(stream_io) is not BoundedManifestHandoffSupervisorEngineApiStreamIo
        ):
            raise ManifestHandoffRegistryUnavailable
        self._gate = gate
        self._io = stream_io

    def __repr__(self) -> str:
        return "ClosedManifestHandoffSupervisorEngineApiExchange()"

    def exchange(self, client_stream, daemon_stream) -> None:
        try:
            if client_stream is daemon_stream:
                raise ManifestHandoffRegistryUnavailable
            request_message = self._io.read(client_stream)
            authorized_request = self._gate.authorize_request(request_message)
            self._io.write(daemon_stream, request_message)
            response_message = self._io.read(daemon_stream)
            authorized_response = self._gate.authorize_response(
                authorized_request, response_message
            )
            self._io.write(client_stream, self._encode(authorized_response))
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _encode(
        response: AuthorizedManifestHandoffSupervisorEngineApiResponse,
    ) -> bytes:
        if type(response) is not AuthorizedManifestHandoffSupervisorEngineApiResponse:
            raise ManifestHandoffRegistryUnavailable
        reason = _REASONS.get(response.status)
        if reason is None:
            raise ManifestHandoffRegistryUnavailable
        start = f"HTTP/1.1 {response.status} {reason}\r\n".encode("ascii")
        if response.content_type is None:
            if response.body != b"":
                raise ManifestHandoffRegistryUnavailable
            return start + b"connection: close\r\n\r\n"
        if response.content_type != "application/json" or not response.body:
            raise ManifestHandoffRegistryUnavailable
        return (
            start
            + b"connection: close\r\n"
            + b"content-type: application/json\r\n"
            + f"content-length: {len(response.body)}\r\n\r\n".encode("ascii")
            + response.body
        )
