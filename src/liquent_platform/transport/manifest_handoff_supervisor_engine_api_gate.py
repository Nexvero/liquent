"""I/O-free closed gate composition for the future Engine API proxy."""

from __future__ import annotations

from dataclasses import dataclass, field

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_http11_framing import (
    ClosedManifestHandoffSupervisorEngineApiHttp11Framing,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_proxy_policy import (
    AuthorizedManifestHandoffSupervisorCreateRequest,
    AuthorizedManifestHandoffSupervisorEngineApiRoute,
    ClosedManifestHandoffSupervisorCreateRequestPolicy,
    ClosedManifestHandoffSupervisorEngineApiRoutePolicy,
    ManifestHandoffSupervisorEngineApiOperation,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_response_policy import (
    AuthorizedManifestHandoffSupervisorEngineApiResponse,
    ClosedManifestHandoffSupervisorEngineApiResponsePolicy,
)


@dataclass(frozen=True, slots=True)
class AuthorizedManifestHandoffSupervisorEngineApiRequest:
    route: AuthorizedManifestHandoffSupervisorEngineApiRoute
    create: AuthorizedManifestHandoffSupervisorCreateRequest | None
    _gate_identity: object = field(repr=False, compare=False)


class ClosedManifestHandoffSupervisorEngineApiGate:
    """Apply every pure request and response gate in a fixed order."""

    __slots__ = ("_create", "_framing", "_identity", "_response", "_route")

    def __init__(
        self,
        create_policy: ClosedManifestHandoffSupervisorCreateRequestPolicy,
        *,
        framing: ClosedManifestHandoffSupervisorEngineApiHttp11Framing | None = None,
        route_policy: ClosedManifestHandoffSupervisorEngineApiRoutePolicy | None = None,
        response_policy: ClosedManifestHandoffSupervisorEngineApiResponsePolicy | None = None,
    ) -> None:
        framing = framing or ClosedManifestHandoffSupervisorEngineApiHttp11Framing()
        route_policy = route_policy or ClosedManifestHandoffSupervisorEngineApiRoutePolicy()
        response_policy = response_policy or ClosedManifestHandoffSupervisorEngineApiResponsePolicy()
        if (
            type(create_policy) is not ClosedManifestHandoffSupervisorCreateRequestPolicy
            or type(framing) is not ClosedManifestHandoffSupervisorEngineApiHttp11Framing
            or type(route_policy) is not ClosedManifestHandoffSupervisorEngineApiRoutePolicy
            or type(response_policy) is not ClosedManifestHandoffSupervisorEngineApiResponsePolicy
        ):
            raise ManifestHandoffRegistryUnavailable
        self._create = create_policy
        self._framing = framing
        self._route = route_policy
        self._response = response_policy
        self._identity = object()

    def __repr__(self) -> str:
        return "ClosedManifestHandoffSupervisorEngineApiGate()"

    def authorize_request(
        self, message: bytes
    ) -> AuthorizedManifestHandoffSupervisorEngineApiRequest:
        try:
            framed = self._framing.decode_request(message)
            route = self._route.authorize(framed.method, framed.target, framed.body)
            create = None
            if route.operation is ManifestHandoffSupervisorEngineApiOperation.CREATE:
                if framed.body is None:
                    raise ManifestHandoffRegistryUnavailable
                create = self._create.authorize(framed.body)
            return AuthorizedManifestHandoffSupervisorEngineApiRequest(
                route, create, self._identity
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None

    def authorize_response(
        self,
        request: AuthorizedManifestHandoffSupervisorEngineApiRequest,
        message: bytes,
    ) -> AuthorizedManifestHandoffSupervisorEngineApiResponse:
        try:
            if (
                type(request) is not AuthorizedManifestHandoffSupervisorEngineApiRequest
                or request._gate_identity is not self._identity
            ):
                raise ManifestHandoffRegistryUnavailable
            framed = self._framing.decode_response(message)
            return self._response.authorize(
                request.route.operation,
                framed.status,
                framed.content_type,
                framed.body,
            )
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
