"""The composed adapter for the OIDC authorization code verifier port."""

from collections.abc import Callable
from datetime import datetime

from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_id_token_verifier import (
    _verify_oidc_id_token_for_adapter,
)
from liquent_platform.identity.oidc_jwks_cache import InMemoryOidcJwksCache
from liquent_platform.identity.oidc_token_exchange import OidcTokenEndpointClient
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
    OidcVerificationUnavailable,
)
from liquent_platform.identity.ports import ActiveOidcClientConfigurationLookup


class ComposedOidcAuthorizationCodeVerifier:
    """Compose the existing building blocks into the LQ-157 port.

    Adds no cryptography, no second JOSE parser, no duplicate key selection, and
    no network access of its own: the token endpoint client and the JWKS cache
    are the only things that reach a provider.

    The clock is a required dependency with no default, so no hidden system time
    can decide validity. It is read exactly once per verification and the same
    value is reused if a second verification follows.
    """

    def __init__(
        self,
        configurations: ActiveOidcClientConfigurationLookup,
        token_endpoint: OidcTokenEndpointClient,
        jwks_cache: InMemoryOidcJwksCache,
        now: Callable[[], datetime],
    ) -> None:
        self._configurations = configurations
        self._token_endpoint = token_endpoint
        self._jwks_cache = jwks_cache
        self._now = now

    def verify_authorization_code(
        self, verification: OidcAuthorizationCodeVerification
    ) -> ExternalIdentity | None:
        """Redeem one code and return only the identity it fully proves.

        ``None`` is the single business rejection and distinguishes nothing.
        OidcVerificationUnavailable means the verification could not be carried
        out at all; it carries no code, token, nonce, verifier, issuer, URI,
        provider text, header, claim, key, or configuration value.

        The transaction was already claimed before this port, so neither result
        is retryable: nothing is rolled back and nothing is retried here.
        """

        try:
            return self._verify(verification)
        except OidcVerificationUnavailable as error:
            # Only an already neutral error whose own chain is clean keeps its
            # identity; one that still carries an inner error is replaced here.
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            # Any unexpected fault from the lookup, the token client, the cache,
            # the clock, or a verification pass ends the same way.
            # BaseException is deliberately not caught.
            pass

        # Raised outside the handler, so the replacement carries neither a cause
        # nor a context and no original detail is reachable through it.
        raise OidcVerificationUnavailable

    def _verify(
        self, verification: OidcAuthorizationCodeVerification
    ) -> ExternalIdentity | None:
        # Read once and passed on as the very same object, so a rotation during
        # this call can never mix a token endpoint, a JWKS, and an issuer from
        # different configurations.
        configuration = self._configurations.get_active_configuration()
        if configuration is None:
            return None
        if configuration.issuer != verification.expected_issuer:
            # Checked before anything external: no network, cache, or clock.
            return None

        id_token = self._token_endpoint.exchange_authorization_code(
            configuration, verification
        )
        if id_token is None:
            # A valid OAuth rejection of the code; no key set is even fetched.
            return None

        jwks = self._jwks_cache.get_jwks(configuration)
        # Read after the network work, so no stale instant judges the token, and
        # exactly once, so a repeat verification asks the same time question.
        moment = self._read_clock()

        result = _verify_oidc_id_token_for_adapter(
            id_token.value, jwks, configuration, verification, moment
        )
        if result.identity is not None:
            return result.identity
        if not result.refreshable_key_miss:
            return None

        # The one controlled refresh of LQ-168, followed by the one and only
        # repeat. Its outcome is read through ``identity`` alone, so a second
        # miss ends as None rather than as another refresh.
        refreshed = self._jwks_cache.refresh_jwks(configuration)
        return _verify_oidc_id_token_for_adapter(
            id_token.value, refreshed, configuration, verification, moment
        ).identity

    def _read_clock(self) -> datetime:
        moment = self._now()
        # A wrongly typed or naive instant cannot bound a token's validity.
        if not isinstance(moment, datetime):
            raise OidcVerificationUnavailable
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise OidcVerificationUnavailable
        return moment
