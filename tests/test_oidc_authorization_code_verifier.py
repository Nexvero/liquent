import inspect
import json
import traceback
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

import liquent_platform.identity.oidc_authorization_code_verifier as module
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.oidc_authorization_code_verifier import (
    ComposedOidcAuthorizationCodeVerifier,
)
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_jwks_cache import InMemoryOidcJwksCache
from liquent_platform.identity.oidc_token_exchange import OidcIdToken
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
    OidcVerificationUnavailable,
)
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy
from liquent_platform.identity.ports import OidcAuthorizationCodeVerifier

ISSUER = "https://idp.example.test"
JWKS_URI = f"{ISSUER}/jwks"
CLIENT_ID = "liquent-control-plane"
CODE = "authorization-code-1"
VERIFIER = "code-verifier-1"
NONCE = "expected-nonce-1"
SUBJECT = "subject-1"
NOW = datetime(2026, 8, 7, 12, tzinfo=UTC)
IDENTITY = ExternalIdentity(issuer=ISSUER, subject=SUBJECT)

_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)
POLICY = OidcVerificationPolicy(
    connect_timeout=timedelta(seconds=2), read_timeout=timedelta(seconds=5),
    total_timeout=timedelta(seconds=10), token_response_max_bytes=4096,
    jwks_response_max_bytes=4096, jwks_cache_ttl=timedelta(minutes=5),
)
CONFIGURATION = TrustedOidcClientConfiguration(
    issuer=ISSUER, authorization_endpoint=f"{ISSUER}/authorize",
    client_id=CLIENT_ID, scopes=("openid",), token_endpoint=f"{ISSUER}/token",
    redirect_uri="https://app.example.test/v1/session/oidc/callback",
    jwks_uri=JWKS_URI, allowed_signing_algorithms=("RS256",),
    clock_skew=timedelta(seconds=30),
)


def _verification(**overrides: Any) -> OidcAuthorizationCodeVerification:
    return OidcAuthorizationCodeVerification(
        **{"authorization_code": CODE, "expected_issuer": ISSUER,
           "expected_nonce": NONCE, "code_verifier": VERIFIER,
           "redirect_uri": CONFIGURATION.redirect_uri, **overrides}
    )


def _jwks(private: Any = _PRIVATE, kid: str = "key-1") -> dict[str, Any]:
    jwk = json.loads(RSAAlgorithm.to_jwk(private.public_key()))
    jwk.update(kid=kid, use="sig", alg="RS256")
    return {"keys": [jwk]}


def _token(kid: str = "key-1") -> OidcIdToken:
    claims = {"iss": ISSUER, "aud": CLIENT_ID, "sub": SUBJECT, "nonce": NONCE,
              "exp": NOW.timestamp() + 300, "iat": NOW.timestamp() - 5}
    return OidcIdToken(
        jwt.encode(claims, _PRIVATE, algorithm="RS256", headers={"kid": kid})
    )


class Recorder:
    """One stand-in that records its calls and replays queued results."""

    def __init__(self, *results: Any) -> None:
        self.results = list(results)
        self.calls: list[Any] = []

    def _next(self, recorded: Any) -> Any:
        self.calls.append(recorded)
        result = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(result, BaseException):
            raise result
        return result

    def get_active_configuration(self) -> Any:
        return self._next(None)

    def exchange_authorization_code(self, configuration: Any, _: Any) -> Any:
        return self._next(configuration)

    def load_jwks(self, configuration: Any) -> Any:
        return self._next(configuration)

    def __call__(self) -> Any:
        return self._next(None)


def _adapter(
    *, configurations: Any = None, tokens: Any = None, loads: Any = None,
    clock: Any = None,
) -> Any:
    """The adapter plus its four recorders, in call order."""

    parts = (
        configurations or Recorder(CONFIGURATION),
        tokens or Recorder(_token()),
        loads or Recorder(_jwks()),
        clock or Recorder(NOW),
    )
    lookup, token_endpoint, loader, ticks = parts
    return (
        ComposedOidcAuthorizationCodeVerifier(
            lookup, token_endpoint, InMemoryOidcJwksCache(loader, POLICY), ticks
        ),
        *parts,
    )


def test_a_verified_token_needs_one_lookup_one_exchange_and_no_refresh() -> None:
    adapter, lookup, tokens, loads, clock = _adapter()

    assert adapter.verify_authorization_code(_verification()) == IDENTITY
    assert len(lookup.calls) == 1
    # The very same configuration object reaches the token client and the cache.
    assert tokens.calls == [CONFIGURATION] and tokens.calls[0] is CONFIGURATION
    assert len(loads.calls) == 1 and loads.calls[0] is CONFIGURATION
    assert clock.calls == [None]


@pytest.mark.parametrize(
    ("configurations", "verification"),
    [
        (Recorder(None), _verification()),
        (Recorder(CONFIGURATION), _verification(expected_issuer=f"{ISSUER}/other")),
    ],
    ids=["no-active-configuration", "issuer-mismatch"],
)
def test_an_early_rejection_touches_no_network_cache_or_clock(
    configurations: Recorder, verification: OidcAuthorizationCodeVerification
) -> None:
    adapter, _, tokens, loads, clock = _adapter(configurations=configurations)

    assert adapter.verify_authorization_code(verification) is None
    assert tokens.calls == [] and loads.calls == [] and clock.calls == []


def test_a_refused_code_is_rejected_without_fetching_any_key_set() -> None:
    adapter, _, tokens, loads, clock = _adapter(tokens=Recorder(None))

    assert adapter.verify_authorization_code(_verification()) is None
    assert len(tokens.calls) == 1
    assert loads.calls == [] and clock.calls == []


def test_a_definitive_rejection_never_refreshes() -> None:
    # Signed by a key the trusted set does not hold, under a known kid.
    adapter, _, tokens, loads, _ = _adapter(loads=Recorder(_jwks(_OTHER)))

    assert adapter.verify_authorization_code(_verification()) is None
    assert len(tokens.calls) == 1
    # A refresh would show as a second load.
    assert len(loads.calls) == 1


def _record_verifications(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Observe the orchestration count without a production seam."""

    seen: list[Any] = []
    original = module._verify_oidc_id_token_for_adapter

    def recording(id_token: Any, jwks: Any, configuration: Any, *rest: Any) -> Any:
        seen.append((id_token, configuration, rest[-1]))
        return original(id_token, jwks, configuration, *rest)

    monkeypatch.setattr(module, "_verify_oidc_id_token_for_adapter", recording)
    return seen


def test_an_unknown_kid_costs_one_refresh_and_one_repeat_at_the_same_instant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _record_verifications(monkeypatch)
    adapter, lookup, tokens, loads, clock = _adapter(
        tokens=Recorder(_token(kid="rotated-in")),
        loads=Recorder(_jwks(kid="retired"), _jwks(kid="rotated-in")),
    )

    assert adapter.verify_authorization_code(_verification()) == IDENTITY
    assert len(seen) == 2 and len(loads.calls) == 2  # one get_jwks, one refresh
    assert len(tokens.calls) == 1 and len(lookup.calls) == 1
    # One clock read, and both passes judge the very same instant.
    assert clock.calls == [None]
    assert seen[0][2] is seen[1][2]
    assert seen[0][1] is seen[1][1] is CONFIGURATION


@pytest.mark.parametrize(
    ("refreshed", "expected"),
    [
        (_jwks(kid="still-retired"), None),
        (_jwks(_OTHER, kid="rotated-in"), None),
    ],
    ids=["second-miss", "second-rejection"],
)
def test_the_second_pass_is_the_last_one(
    monkeypatch: pytest.MonkeyPatch, refreshed: dict[str, Any], expected: Any
) -> None:
    seen = _record_verifications(monkeypatch)
    adapter, _, tokens, loads, _ = _adapter(
        tokens=Recorder(_token(kid="rotated-in")),
        loads=Recorder(_jwks(kid="retired"), refreshed),
    )

    assert adapter.verify_authorization_code(_verification()) == expected
    assert len(seen) == 2 and len(loads.calls) == 2 and len(tokens.calls) == 1



def _faulty(
    stage: str, error: BaseException, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Arguments that make exactly one stage fail with ``error``."""

    simple = {"lookup": "configurations", "token": "tokens",
              "get-jwks": "loads", "clock": "clock"}
    if stage in simple:
        return {simple[stage]: Recorder(error)}

    # The refresh stages need a first miss before the fault can be reached.
    if stage != "refresh":
        index, original, calls = (
            1 if stage == "first-verification" else 2,
            module._verify_oidc_id_token_for_adapter,
            [0],
        )

        def once(*passed: Any) -> Any:
            calls[0] += 1
            if calls[0] == index:
                raise error
            return original(*passed)

        monkeypatch.setattr(module, "_verify_oidc_id_token_for_adapter", once)
    return {
        "tokens": Recorder(_token(kid="rotated-in")),
        "loads": Recorder(
            _jwks(kid="retired"),
            error if stage == "refresh" else _jwks(kid="rotated-in"),
        ),
    }


@pytest.mark.parametrize(
    ("stage", "detail"),
    [
        ("lookup", "LOOKUP-DETAIL"),
        ("token", "TOKEN-DETAIL"),
        ("get-jwks", "LOADER-DETAIL"),
        ("clock", "CLOCK-DETAIL"),
        ("naive-clock", None),
        ("first-verification", "VERIFY-ONE-DETAIL"),
        ("refresh", "REFRESH-DETAIL"),
        ("second-verification", "VERIFY-TWO-DETAIL"),
        ("already-neutral", None),
    ],
)
def test_a_technical_fault_at_any_stage_is_neutral_and_detail_free(
    monkeypatch: pytest.MonkeyPatch, stage: str, detail: str | None
) -> None:
    neutral = OidcVerificationUnavailable()
    if stage == "naive-clock":
        arguments: dict[str, Any] = {"clock": Recorder(NOW.replace(tzinfo=None))}
    elif stage == "already-neutral":
        arguments = {"configurations": Recorder(neutral)}
    else:
        arguments = _faulty(stage, RuntimeError(detail), monkeypatch)

    adapter, *_ = _adapter(**arguments)

    with pytest.raises(OidcVerificationUnavailable) as raised:
        adapter.verify_authorization_code(_verification())

    # The public boundary always ends in a fully detail-free chain, including
    # for the neutral errors the cache raises with an inner context of its own.
    assert raised.value.args == ("oidc_verification_unavailable",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    rendered = f"{raised.value!r}{raised.value.args}"
    for secret in (CODE, VERIFIER, NONCE, ISSUER, JWKS_URI, SUBJECT):
        assert secret not in rendered
    if stage == "already-neutral":
        # Clean on arrival, so the very same object keeps its identity.
        assert raised.value is neutral
    elif detail is not None:
        assert detail not in "".join(
            traceback.format_exception(
                type(raised.value), raised.value, raised.value.__traceback__
            )
        )


@pytest.mark.parametrize("stage", ["clock", "refresh", "second-verification"])
def test_a_base_exception_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    arguments = _faulty(stage, KeyboardInterrupt(), monkeypatch)

    adapter, *_ = _adapter(**arguments)

    with pytest.raises(KeyboardInterrupt):
        adapter.verify_authorization_code(_verification())


def test_the_adapter_satisfies_the_port_and_hides_its_collaborators() -> None:
    adapter, *_ = _adapter()
    port: OidcAuthorizationCodeVerifier = adapter

    assert inspect.signature(
        type(adapter).verify_authorization_code
    ) == inspect.signature(
        OidcAuthorizationCodeVerifier.verify_authorization_code
    )
    assert port.verify_authorization_code(_verification()) == IDENTITY
    rendered = repr(adapter)
    for secret in (ISSUER, JWKS_URI, CLIENT_ID, "keys", "RSA", "Recorder"):
        assert secret not in rendered
