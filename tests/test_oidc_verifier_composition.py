from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx2
import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
    OidcVerificationUnavailable,
)
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_verifier_composition import (
    OidcVerifierComposition,
    compose_oidc_verifier,
)

NOW = datetime(2026, 8, 12, tzinfo=UTC)
POLICY = OidcVerificationPolicy(
    connect_timeout=timedelta(seconds=1),
    read_timeout=timedelta(seconds=2),
    total_timeout=timedelta(seconds=3),
    token_response_max_bytes=4096,
    jwks_response_max_bytes=8192,
    jwks_cache_ttl=timedelta(minutes=5),
)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'composition.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _verification(issuer: str = "https://issuer.example") -> OidcAuthorizationCodeVerification:
    return OidcAuthorizationCodeVerification(
        authorization_code="code-193",
        expected_issuer=issuer,
        expected_nonce="nonce-193",
        code_verifier="verifier-193",
        redirect_uri="https://app.example/callback",
    )


def _insert_configuration(engine: Engine, *, active: bool = True) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO oidc_trust_revisions"
                " (revision_id,issuer,authorization_endpoint,client_id,redirect_uri,"
                " scopes,token_endpoint,jwks_uri,allowed_signing_algorithms,"
                " clock_skew_microseconds) VALUES"
                " (:revision,:issuer,:authorization,:client,:redirect,:scopes,"
                " :token,:jwks,:algorithms,0)"
            ),
            {
                "revision": b"revision-193",
                "issuer": b"https://issuer.example",
                "authorization": b"https://issuer.example/authorize",
                "client": b"client-193",
                "redirect": b"https://app.example/callback",
                "scopes": b'["openid"]',
                "token": b"https://issuer.example/token",
                "jwks": b"https://issuer.example/keys",
                "algorithms": b'["RS256"]',
            },
        )
        connection.execute(
            text(
                "INSERT INTO oidc_client_configuration"
                " (singleton_key,active,issuer,authorization_endpoint,client_id,"
                " redirect_uri,scopes,token_endpoint,jwks_uri,"
                " allowed_signing_algorithms,clock_skew_microseconds,revision_id) VALUES"
                " (1,:active,:issuer,:authorization,:client,:redirect,:scopes,"
                " :token,:jwks,:algorithms,0,:revision)"
            ),
            {
                "active": active,
                "revision": b"revision-193",
                "issuer": b"https://issuer.example",
                "authorization": b"https://issuer.example/authorize",
                "client": b"client-193",
                "redirect": b"https://app.example/callback",
                "scopes": b'["openid"]',
                "token": b"https://issuer.example/token",
                "jwks": b"https://issuer.example/keys",
                "algorithms": b'["RS256"]',
            },
        )


def test_composition_uses_one_lookup_client_policy_and_each_clock(engine: Engine) -> None:
    client = httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(500)))
    ticks = lambda: 10.0
    wall = lambda: NOW
    try:
        composition = compose_oidc_verifier(
            engine, client, POLICY, now=wall, monotonic=ticks
        )
        assert isinstance(composition, OidcVerifierComposition)
        assert composition.verifier._configurations is composition.configurations
        token_endpoint = composition.verifier._token_endpoint
        cache = composition.verifier._jwks_cache
        assert token_endpoint._client is client
        assert token_endpoint._policy is POLICY
        assert token_endpoint._monotonic is ticks
        assert cache._loader._client is client
        assert cache._loader._policy is POLICY
        assert cache._loader._monotonic is ticks
        assert cache._policy is POLICY and cache._monotonic is ticks
        assert composition.verifier._now is wall
    finally:
        client.close()


def test_composition_performs_no_io_and_does_not_own_resources(engine: Engine) -> None:
    requests: list[httpx2.Request] = []

    def record(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(500)

    client = httpx2.Client(transport=httpx2.MockTransport(record))
    composition = compose_oidc_verifier(engine, client, POLICY)
    assert requests == []
    assert repr(composition) == "OidcVerifierComposition()"
    assert client.is_closed is False
    assert engine.pool is not None
    client.close()


def test_empty_or_deactivated_configuration_rejects_without_network(
    engine: Engine,
) -> None:
    calls = 0

    def unexpected(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(500)

    client = httpx2.Client(transport=httpx2.MockTransport(unexpected))
    try:
        composition = compose_oidc_verifier(engine, client, POLICY, now=lambda: NOW)
        assert composition.verifier.verify_authorization_code(_verification()) is None
        _insert_configuration(engine, active=False)
        assert composition.verifier.verify_authorization_code(_verification()) is None
        assert calls == 0
    finally:
        client.close()


def test_current_issuer_mismatch_rejects_before_network_or_clock(engine: Engine) -> None:
    _insert_configuration(engine)
    calls = 0

    def unexpected(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(500)

    client = httpx2.Client(transport=httpx2.MockTransport(unexpected))
    try:
        composition = compose_oidc_verifier(
            engine,
            client,
            POLICY,
            now=lambda: (_ for _ in ()).throw(AssertionError("clock read")),
        )
        assert composition.verifier.verify_authorization_code(
            _verification("https://other.example")
        ) is None
        assert calls == 0
    finally:
        client.close()


def test_configuration_failure_is_neutral_verification_unavailability(
    tmp_path: Path,
) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    client = httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(500)))
    try:
        composition = compose_oidc_verifier(engine, client, POLICY, now=lambda: NOW)
        with pytest.raises(OidcVerificationUnavailable) as raised:
            composition.verifier.verify_authorization_code(_verification())
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
    finally:
        client.close()
        engine.dispose()
