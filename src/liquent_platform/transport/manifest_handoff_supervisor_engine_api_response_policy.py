"""Closed response policy for the future local supervisor Engine API proxy."""

from __future__ import annotations

from dataclasses import dataclass
import json

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import (
    ManifestHandoffSupervisorEngineApiOperation,
)


_JSON = "application/json"
_MAX_JSON_BYTES = 1_048_576


@dataclass(frozen=True, slots=True)
class AuthorizedManifestHandoffSupervisorEngineApiResponse:
    status: int
    content_type: str | None
    body: bytes


class ClosedManifestHandoffSupervisorEngineApiResponsePolicy:
    """Validate and normalize one operation-bound daemon response."""

    def authorize(
        self,
        operation: ManifestHandoffSupervisorEngineApiOperation,
        status: int,
        content_type: str | None,
        body: bytes,
    ) -> AuthorizedManifestHandoffSupervisorEngineApiResponse:
        try:
            if (
                type(operation) is not ManifestHandoffSupervisorEngineApiOperation
                or type(status) is not int
                or type(body) is not bytes
                or (content_type is not None and type(content_type) is not str)
            ):
                raise ManifestHandoffRegistryUnavailable
            if operation is ManifestHandoffSupervisorEngineApiOperation.INSPECT:
                if status == 404:
                    return self._absent(content_type, body)
                return self._json(status, content_type, body, expected=200, root=dict)
            if operation is ManifestHandoffSupervisorEngineApiOperation.FIND:
                return self._json(status, content_type, body, expected=200, root=list)
            if operation is ManifestHandoffSupervisorEngineApiOperation.CREATE:
                return self._json(status, content_type, body, expected=201, root=dict)
            if operation is ManifestHandoffSupervisorEngineApiOperation.WAIT:
                return self._json(status, content_type, body, expected=200, root=dict)
            if operation is ManifestHandoffSupervisorEngineApiOperation.START:
                return self._empty(status, content_type, body, statuses=(204,))
            if operation in {
                ManifestHandoffSupervisorEngineApiOperation.STOP,
                ManifestHandoffSupervisorEngineApiOperation.KILL,
            }:
                return self._empty(status, content_type, body, statuses=(204, 304))
            raise ManifestHandoffRegistryUnavailable
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _json(status, content_type, body, *, expected, root):
        if (
            status != expected
            or content_type != _JSON
            or not body
            or len(body) > _MAX_JSON_BYTES
        ):
            raise ManifestHandoffRegistryUnavailable
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_unique)
        if type(value) is not root:
            raise ManifestHandoffRegistryUnavailable
        return AuthorizedManifestHandoffSupervisorEngineApiResponse(
            status, _JSON, body
        )

    @staticmethod
    def _empty(status, content_type, body, *, statuses):
        if status not in statuses or content_type is not None or body != b"":
            raise ManifestHandoffRegistryUnavailable
        return AuthorizedManifestHandoffSupervisorEngineApiResponse(
            status, None, b""
        )

    @staticmethod
    def _absent(content_type, body):
        if not (
            (content_type is None and body == b"")
            or (content_type == _JSON and body == b"{}")
        ):
            raise ManifestHandoffRegistryUnavailable
        return AuthorizedManifestHandoffSupervisorEngineApiResponse(404, None, b"")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestHandoffRegistryUnavailable
        result[key] = value
    return result
