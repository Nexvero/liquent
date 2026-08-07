"""One bounded in-memory slot for an already controlled JWKS document."""

import math
import time
from collections.abc import Callable, Mapping

from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_jwks_retrieval import OidcJwksEndpointClient
from liquent_platform.identity.oidc_verification import OidcVerificationUnavailable
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy


class InMemoryOidcJwksCache:
    """Hold at most one freshly loaded key set for the active configuration.

    The platform has exactly one active OIDC configuration, so capacity is
    bounded **structurally** rather than by an eviction rule: there is a single
    slot, and a different ``jwks_uri`` replaces it. A sequence of rotated
    configurations therefore cannot accumulate keys or issuers, and because the
    slot is keyed on the *configured* URI, no token can create its own cache
    partition.

    The instance keeps two private values and nothing else: ``_slot`` holds at
    most one key set with its monotonic expiry, and ``_last_clock`` holds at
    most one technical clock reading. Neither is shared between instances and
    neither is global.

    No cache entry, URI, or key material reaches ``repr``, an exception, a log,
    or telemetry. There is no refresh on an unknown ``kid``, no token inspection,
    no retry, no stale-while-error, no background refresh, and no locking.
    """

    def __init__(
        self,
        loader: OidcJwksEndpointClient,
        policy: OidcVerificationPolicy,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._loader = loader
        self._policy = policy
        self._monotonic = monotonic
        self._slot: tuple[str, Mapping[str, object], float] | None = None
        self._last_clock: float | None = None

    def get_jwks(
        self, configuration: TrustedOidcClientConfiguration
    ) -> Mapping[str, object]:
        """Return the cached key set, loading it exactly once when needed.

        A hit requires a byte-identical ``jwks_uri`` and a reading strictly
        before the stored expiry; then no load happens at all. Otherwise the
        slot is dropped **before** any load attempt, so a failure can never
        leave stale material behind, and a new slot is stored only after a
        fully successful load.

        The returned mapping is the snapshot the LQ-166 loader parsed. It is
        handed out as is because the current internal users read it only — this
        is a statement about today's read-only use, not a general mutability
        guarantee.
        """

        now = self._read_clock()
        if self._slot is not None:
            uri, key_set, expires_at = self._slot
            if uri == configuration.jwks_uri and now < expires_at:
                return key_set

        # Expired, a different URI, or empty. Dropping first means a failing
        # load leaves the cache empty rather than serving stale keys.
        self._slot = None
        key_set = self._load(configuration)

        # Measured after the load, so network time is never sold as freshness.
        loaded_at = self._read_clock()
        expires_at = loaded_at + self._policy.jwks_cache_ttl.total_seconds()
        # A positive TTL that produces no strictly later instant in the float
        # range at hand cannot guarantee freshness, so saturation is a
        # technical failure rather than an entry that expires on arrival.
        if not math.isfinite(expires_at) or expires_at <= loaded_at:
            raise OidcVerificationUnavailable
        self._slot = (configuration.jwks_uri, key_set, expires_at)
        return key_set

    def _load(self, configuration: TrustedOidcClientConfiguration) -> Mapping[str, object]:
        try:
            return self._loader.load_jwks(configuration)
        except OidcVerificationUnavailable:
            raise
        except Exception:
            # The loader is a technical dependency; its error text and cause
            # must not escape. BaseException is deliberately not caught.
            raise OidcVerificationUnavailable from None

    def _read_clock(self) -> float:
        try:
            moment = self._monotonic()
            # bool is an int subclass and is never a reading.
            if isinstance(moment, bool) or not isinstance(moment, (int, float)):
                raise OidcVerificationUnavailable
            if not math.isfinite(moment):
                raise OidcVerificationUnavailable
            reading = float(moment)
            # A monotonic clock never steps back within one instance; a tie is
            # still fine.
            if self._last_clock is not None and reading < self._last_clock:
                raise OidcVerificationUnavailable
        except OidcVerificationUnavailable:
            # A clock that cannot decide freshness must not leave anything
            # servable behind.
            self._slot = None
            raise
        except Exception:
            self._slot = None
            raise OidcVerificationUnavailable from None
        self._last_clock = reading
        return reading
