"""Closed bounded read-only protocol for local proxy process health."""

from __future__ import annotations

import json

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_owner import (
    ManifestHandoffSupervisorEngineApiProcessOwner,
)


_REQUESTS = {
    b"GET /live HTTP/1.1\r\nhost: local\r\nconnection: close\r\n\r\n": "live",
    b"GET /ready HTTP/1.1\r\nhost: local\r\nconnection: close\r\n\r\n": "ready",
}
_UNAVAILABLE = "manifest_handoff_supervisor_engine_api_unavailable"
_MAXIMUM_REQUEST_BYTES = 128
_MAXIMUM_BODY_BYTES = 256


class ClosedManifestHandoffSupervisorEngineApiHealthProtocol:
    """Answer two exact local health requests without owning any stream."""

    __slots__ = ("_owner",)

    def __init__(self, owner: ManifestHandoffSupervisorEngineApiProcessOwner) -> None:
        if type(owner) is not ManifestHandoffSupervisorEngineApiProcessOwner:
            raise ManifestHandoffRegistryUnavailable
        self._owner = owner

    def __repr__(self) -> str:
        return "ClosedManifestHandoffSupervisorEngineApiHealthProtocol()"

    def handle(self, request: bytes) -> bytes:
        try:
            if (
                type(request) is not bytes
                or not request
                or len(request) > _MAXIMUM_REQUEST_BYTES
            ):
                raise ManifestHandoffRegistryUnavailable
            operation = _REQUESTS.get(request)
            if operation is None:
                raise ManifestHandoffRegistryUnavailable
            if operation == "live":
                try:
                    snapshot = self._owner.snapshot()
                    value, reason = snapshot.live, snapshot.reason
                except Exception:
                    value, reason = False, _UNAVAILABLE
            else:
                readiness = self._owner.readiness()
                value, reason = readiness.ready, readiness.reason
            if type(value) is not bool or type(reason) is not str or not reason:
                value, reason = False, _UNAVAILABLE
            return self._response(operation, value, reason)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _response(operation: str, value: bool, reason: str) -> bytes:
        body = json.dumps(
            {operation: value, "reason": reason},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        if not body or len(body) > _MAXIMUM_BODY_BYTES:
            body = json.dumps(
                {operation: False, "reason": _UNAVAILABLE},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("ascii")
            value = False
        status = b"200 OK" if value else b"503 Service Unavailable"
        return (
            b"HTTP/1.1 " + status + b"\r\n"
            b"connection: close\r\n"
            b"content-type: application/json\r\n"
            + f"content-length: {len(body)}\r\n\r\n".encode("ascii")
            + body
        )
