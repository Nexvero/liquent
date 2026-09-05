"""Internal composition of persistent OIDC trust and code verification."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx2
from sqlalchemy import Engine

from liquent_platform.identity.oidc_authorization_code_verifier import (
    ComposedOidcAuthorizationCodeVerifier,
)
from liquent_platform.identity.oidc_jwks_cache import InMemoryOidcJwksCache
from liquent_platform.identity.oidc_jwks_retrieval import OidcJwksEndpointClient
from liquent_platform.identity.oidc_token_exchange import OidcTokenEndpointClient
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy
from liquent_platform.persistence.oidc_client_configuration import (
    DatabaseActiveOidcClientConfiguration,
)


@dataclass(frozen=True, slots=True)
class OidcVerifierComposition:
    """The two capabilities outer composition needs, without resource ownership."""

    configurations: DatabaseActiveOidcClientConfiguration
    verifier: ComposedOidcAuthorizationCodeVerifier

    def __repr__(self) -> str:
        return "OidcVerifierComposition()"


def compose_oidc_verifier(
    engine: Engine,
    client: httpx2.Client,
    policy: OidcVerificationPolicy,
    *,
    now: Callable[[], datetime] | None = None,
    monotonic: Callable[[], float] | None = None,
) -> OidcVerifierComposition:
    """Wire existing trust and verification adapters around owned resources.

    The caller retains ownership of both the database engine and HTTP client.
    This function performs no I/O, lookup, discovery, verification, or close.
    """

    wall_clock = now or (lambda: datetime.now(UTC))
    technical_clock = monotonic or time.monotonic
    configurations = DatabaseActiveOidcClientConfiguration(engine)
    token_endpoint = OidcTokenEndpointClient(client, policy, technical_clock)
    jwks_loader = OidcJwksEndpointClient(client, policy, technical_clock)
    jwks_cache = InMemoryOidcJwksCache(jwks_loader, policy, technical_clock)
    verifier = ComposedOidcAuthorizationCodeVerifier(
        configurations,
        token_endpoint,
        jwks_cache,
        wall_clock,
    )
    return OidcVerifierComposition(configurations, verifier)
