import sys
from datetime import timedelta
from typing import Any

import pytest

from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_jwks_cache import InMemoryOidcJwksCache
from liquent_platform.identity.oidc_verification import OidcVerificationUnavailable
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy


ISSUER = "https://idp.example.test"
JWKS_URI = f"{ISSUER}/jwks"
OTHER_JWKS_URI = f"{ISSUER}/jwks/"  # byte-different: one trailing slash
TTL_SECONDS = 300.0

POLICY = OidcVerificationPolicy(
    connect_timeout=timedelta(seconds=2),
    read_timeout=timedelta(seconds=5),
    total_timeout=timedelta(seconds=10),
    token_response_max_bytes=4096,
    jwks_response_max_bytes=4096,
    jwks_cache_ttl=timedelta(seconds=TTL_SECONDS),
)


def _configuration(jwks_uri: str = JWKS_URI) -> TrustedOidcClientConfiguration:
    return TrustedOidcClientConfiguration(
        issuer=ISSUER,
        authorization_endpoint=f"{ISSUER}/authorize",
        client_id="liquent-control-plane",
        redirect_uri="https://app.example.test/v1/session/oidc/callback",
        scopes=("openid",),
        token_endpoint=f"{ISSUER}/token",
        jwks_uri=jwks_uri,
        allowed_signing_algorithms=("RS256",),
        clock_skew=timedelta(seconds=30),
    )


class Loader:
    """A stand-in for the LQ-166 loader, recording every call."""

    def __init__(self, *results: Any) -> None:
        self.results = list(results)
        self.calls: list[str] = []

    def load_jwks(self, configuration: TrustedOidcClientConfiguration) -> Any:
        self.calls.append(configuration.jwks_uri)
        result = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(result, BaseException):
            raise result
        return result


def _key_set(kid: str) -> dict[str, Any]:
    return {"keys": [{"kty": "RSA", "kid": kid}], "meta": "kept"}


def _clock(*readings: Any) -> Any:
    """Yield each reading in turn, then repeat the last; raise an exception."""

    remaining = list(readings)
    last: list[Any] = [None]

    def clock() -> float:
        value = remaining.pop(0) if remaining else last[0]
        if isinstance(value, BaseException):
            raise value
        last[0] = value
        return value

    return clock


def _cache(loader: Loader, clock: Any = None) -> InMemoryOidcJwksCache:
    arguments = {"monotonic": clock} if clock is not None else {}
    return InMemoryOidcJwksCache(loader, POLICY, **arguments)


def test_an_empty_cache_loads_once_and_then_serves_the_same_snapshot() -> None:
    keys = _key_set("a")
    loader = Loader(keys)
    cache = _cache(loader, _clock(0.0, 100.0, 200.0, 100.0 + TTL_SECONDS - 1.0))

    first = cache.get_jwks(_configuration())
    second = cache.get_jwks(_configuration())
    third = cache.get_jwks(_configuration())

    # Stamped after the load, so even just under 100.0 + 300 is still fresh,
    # and every hit hands back the very snapshot the loader parsed.
    assert first is second is third is keys
    assert loader.calls == [JWKS_URI]


@pytest.mark.parametrize(
    ("reading", "loads"),
    [
        (TTL_SECONDS - 0.001, 1),  # strictly before the expiry is still fresh
        (TTL_SECONDS, 2),  # exactly at the expiry already counts as expired
    ],
)
def test_the_ttl_boundary_is_strict(reading: float, loads: int) -> None:
    loader = Loader(_key_set("a"), _key_set("b"))
    cache = _cache(loader, _clock(0.0, 0.0, reading, reading))

    cache.get_jwks(_configuration())
    cache.get_jwks(_configuration())

    assert len(loader.calls) == loads


@pytest.mark.parametrize(
    "reload_result",
    [_key_set("b"), OidcVerificationUnavailable()],
    ids=["reload-succeeds", "reload-fails"],
)
def test_an_expired_slot_is_dropped_before_the_reload(reload_result: Any) -> None:
    first_keys = _key_set("a")
    loader = Loader(first_keys, reload_result)
    cache = _cache(loader, _clock(0.0, 0.0, TTL_SECONDS, TTL_SECONDS, TTL_SECONDS))

    assert cache.get_jwks(_configuration()) is first_keys

    if isinstance(reload_result, BaseException):
        with pytest.raises(OidcVerificationUnavailable):
            cache.get_jwks(_configuration())
        # Nothing stale survived the failure, so the next call loads again.
        loader.results = [_key_set("c")]
        assert cache.get_jwks(_configuration())["keys"][0]["kid"] == "c"
    else:
        # The expired snapshot is replaced outright, never merged or reused.
        assert cache.get_jwks(_configuration()) is reload_result
        assert loader.calls == [JWKS_URI, JWKS_URI]


@pytest.mark.parametrize(
    ("second_uri", "second_result", "expected_kid"),
    [
        (JWKS_URI, _key_set("b"), "a"),  # byte-identical: a hit, no load
        (OTHER_JWKS_URI, _key_set("b"), "b"),  # one trailing slash: reloads
        (OTHER_JWKS_URI, OidcVerificationUnavailable(), None),  # and may fail
    ],
    ids=["identical-uri", "different-uri", "different-uri-fails"],
)
def test_the_uri_is_compared_byte_for_byte(
    second_uri: str, second_result: Any, expected_kid: str | None
) -> None:
    first_keys = _key_set("a")
    loader = Loader(first_keys, second_result)
    cache = _cache(loader, _clock(0.0, 0.0, 1.0, 1.0, 1.0))
    assert cache.get_jwks(_configuration()) is first_keys

    if expected_kid is not None:
        served = cache.get_jwks(_configuration(second_uri))
        assert served["keys"][0]["kid"] == expected_kid
        return

    with pytest.raises(OidcVerificationUnavailable):
        cache.get_jwks(_configuration(second_uri))
    # Back on the original URI the old slot is gone; 1.0 would still be fresh.
    loader.results = [_key_set("c")]
    assert cache.get_jwks(_configuration())["keys"][0]["kid"] == "c"


@pytest.mark.parametrize(
    "failure",
    [
        OidcVerificationUnavailable(),
        RuntimeError("LOADER-INTERNAL-DETAIL"),
    ],
    ids=["already-neutral", "unexpected-normal-error"],
)
def test_a_loader_failure_is_neutral_and_leaves_the_cache_empty(
    failure: Exception,
) -> None:
    loader = Loader(failure)
    cache = _cache(loader, _clock(0.0, 1.0))

    with pytest.raises(OidcVerificationUnavailable) as raised:
        cache.get_jwks(_configuration())

    assert raised.value.args == ("oidc_verification_unavailable",)
    assert "LOADER-INTERNAL-DETAIL" not in f"{raised.value!r}{raised.value.args}"
    assert raised.value.__cause__ is None
    # Nothing was stored, so the next call loads again.
    loader.results = [_key_set("a")]
    assert cache.get_jwks(_configuration())["keys"][0]["kid"] == "a"


@pytest.mark.parametrize(
    ("loader_results", "clock"),
    [
        ([KeyboardInterrupt()], _clock(0.0)),
        ([_key_set("a")], _clock(0.0, KeyboardInterrupt())),
    ],
    ids=["from-the-loader", "from-the-clock"],
)
def test_a_base_exception_propagates_unchanged(
    loader_results: list[Any], clock: Any
) -> None:
    cache = _cache(Loader(*loader_results), clock)

    with pytest.raises(KeyboardInterrupt):
        cache.get_jwks(_configuration())


@pytest.mark.parametrize(
    "clock",
    [
        _clock(0.0, 1.0, float("nan"), 2.0),
        _clock(0.0, 1.0, True, 2.0),
        _clock(0.0, 1.0, "later", 2.0),
        _clock(0.0, 1.0, 0.5, 2.0),  # steps back on a later get_jwks call
        _clock(0.0, 1.0, RuntimeError("CLOCK-INTERNAL-DETAIL"), 2.0),
    ],
    ids=["not-finite", "bool", "not-a-number", "steps-back", "raises"],
)
def test_an_unusable_clock_discards_the_slot_and_fails_neutrally(clock: Any) -> None:
    keys = _key_set("a")
    loader = Loader(keys, _key_set("b"))
    cache = _cache(loader, clock)
    assert cache.get_jwks(_configuration()) is keys

    with pytest.raises(OidcVerificationUnavailable) as raised:
        cache.get_jwks(_configuration())

    assert raised.value.args == ("oidc_verification_unavailable",)
    assert "CLOCK-INTERNAL-DETAIL" not in f"{raised.value!r}{raised.value.args}"
    # 2.0 is still inside the expiry, so a surviving slot would serve "a".
    assert cache.get_jwks(_configuration())["keys"][0]["kid"] == "b"


def test_a_saturated_expiry_is_a_neutral_failure_and_nothing_leaks() -> None:
    """At the float ceiling the expiry cannot grow, so freshness is unprovable."""

    huge = sys.float_info.max
    assert huge + TTL_SECONDS == huge
    loader = Loader(_key_set("a"), _key_set("b"))
    cache = _cache(loader, _clock(huge))

    # The load happens, but its result is never handed out or stored.
    with pytest.raises(OidcVerificationUnavailable) as raised:
        cache.get_jwks(_configuration())
    assert len(loader.calls) == 1
    assert raised.value.args == ("oidc_verification_unavailable",)

    # Nothing was cached, so the next call loads again and fails the same way.
    with pytest.raises(OidcVerificationUnavailable):
        cache.get_jwks(_configuration())
    assert len(loader.calls) == 2

    # The URI and the key material stay out of the object's representation.
    rendered = repr(cache)
    for secret in (JWKS_URI, ISSUER, "kty", "RSA"):
        assert secret not in rendered
