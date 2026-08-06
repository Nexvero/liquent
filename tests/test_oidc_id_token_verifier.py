import inspect
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_id_token_verifier import (
    SUPPORTED_SIGNING_ALGORITHMS,
    verify_oidc_id_token,
)
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
    OidcVerificationUnavailable,
)


ISSUER = "https://idp.example.test"
CLIENT_ID = "liquent-control-plane"
NONCE = "expected-nonce-1"
SUBJECT = "subject-1"
NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)
SKEW = timedelta(seconds=30)

# One locally generated key pair per module: no network and no real provider.
_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _public_jwk(private: Any = _PRIVATE, **overrides: Any) -> dict[str, Any]:
    jwk = json.loads(RSAAlgorithm.to_jwk(private.public_key()))
    jwk.update(kid="key-1", use="sig", alg="RS256")
    jwk.update(overrides)
    return jwk


def _jwks(*keys: dict[str, Any]) -> dict[str, Any]:
    return {"keys": list(keys or (_public_jwk(),))}


def _configuration(**overrides: Any) -> TrustedOidcClientConfiguration:
    arguments: dict[str, Any] = {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/authorize",
        "client_id": CLIENT_ID,
        "redirect_uri": "https://app.example.test/v1/session/oidc/callback",
        "scopes": ("openid",),
        "token_endpoint": f"{ISSUER}/token",
        "jwks_uri": f"{ISSUER}/jwks",
        "allowed_signing_algorithms": ("RS256",),
        "clock_skew": SKEW,
    }
    arguments.update(overrides)
    return TrustedOidcClientConfiguration(**arguments)


def _verification(**overrides: Any) -> OidcAuthorizationCodeVerification:
    arguments: dict[str, Any] = {
        "authorization_code": "code-1",
        "expected_issuer": ISSUER,
        "expected_nonce": NONCE,
        "code_verifier": "verifier-1",
        "redirect_uri": "https://app.example.test/v1/session/oidc/callback",
    }
    arguments.update(overrides)
    return OidcAuthorizationCodeVerification(**arguments)


def _token(
    *,
    private: Any = _PRIVATE,
    algorithm: str = "RS256",
    headers: dict[str, Any] | None = None,
    drop: tuple[str, ...] = (),
    **claims: Any,
) -> str:
    payload: dict[str, Any] = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": SUBJECT,
        "nonce": NONCE,
        "exp": NOW.timestamp() + 300,
        "iat": NOW.timestamp() - 5,
    }
    payload.update(claims)
    for name in drop:
        payload.pop(name, None)
    return jwt.encode(
        payload, private, algorithm=algorithm, headers={"kid": "key-1", **(headers or {})}
    )


def _verify(**overrides: Any) -> ExternalIdentity | None:
    arguments: dict[str, Any] = {
        "id_token": _token(),
        "jwks": _jwks(),
        "configuration": _configuration(),
        "verification": _verification(),
        "now": NOW,
    }
    arguments.update(overrides)
    return verify_oidc_id_token(**arguments)


# --- 1. Success ------------------------------------------------------------

def test_a_valid_token_yields_the_configured_issuer_and_its_subject() -> None:
    result = _verify()

    assert result == ExternalIdentity(issuer=ISSUER, subject=SUBJECT)
    # The issuer comes from the trusted configuration, not from a claim.
    assert result is not None and result.issuer == _configuration().issuer


# --- 2. Trust snapshot -----------------------------------------------------

def test_a_configuration_issuer_differing_from_the_expectation_is_rejected() -> None:
    assert _verify(verification=_verification(expected_issuer="https://other.test")) is None


# --- 3. Algorithms ---------------------------------------------------------

def test_an_algorithm_outside_the_configured_allowlist_is_rejected() -> None:
    assert _verify(configuration=_configuration(allowed_signing_algorithms=("ES256",))) is None


def test_a_symmetric_algorithm_is_never_supported() -> None:
    """Refused by the internal allowlist even when configuration permits it.

    The JWK deliberately carries no ``alg``, so the key filter cannot be what
    rejects the token: only the internal allowlist can, and it must do so
    before any key is built.
    """

    token = jwt.encode(
        {"iss": ISSUER, "aud": CLIENT_ID, "sub": SUBJECT, "nonce": NONCE,
         "exp": NOW.timestamp() + 300, "iat": NOW.timestamp() - 5},
        "shared-secret-at-least-32-bytes-long!",
        algorithm="HS256",
        headers={"kid": "key-1"},
    )
    key = _public_jwk()
    key.pop("alg")

    assert _verify(
        id_token=token,
        jwks=_jwks(key),
        configuration=_configuration(allowed_signing_algorithms=("RS256", "HS256")),
    ) is None


def test_the_internal_allowlist_holds_only_asymmetric_algorithms() -> None:
    assert SUPPORTED_SIGNING_ALGORITHMS == {
        "RS256", "RS384", "RS512",
        "PS256", "PS384", "PS512",
        "ES256", "ES384", "ES512",
        "EdDSA",
    }


def test_an_unsigned_token_is_rejected() -> None:
    token = jwt.encode(
        {"iss": ISSUER, "aud": CLIENT_ID, "sub": SUBJECT, "nonce": NONCE,
         "exp": NOW.timestamp() + 300, "iat": NOW.timestamp() - 5},
        key=None,
        algorithm=None,
        headers={"kid": "key-1"},
    )

    assert _verify(id_token=token) is None
    # Defence in depth: LQ-156 already refuses "none" in the configuration, so
    # such a token can never be allowlisted in the first place.
    with pytest.raises(ValueError):
        _configuration(allowed_signing_algorithms=("RS256", "none"))


# --- 4. Token-controlled key sources ---------------------------------------

@pytest.mark.parametrize("name", ["jku", "x5u", "jwk"])
def test_a_token_controlled_key_source_is_refused(name: str) -> None:
    value = _public_jwk() if name == "jwk" else "https://evil.example.test/keys"

    assert _verify(id_token=_token(headers={name: value})) is None


# --- 5. Key selection ------------------------------------------------------

def test_a_known_unique_kid_selects_its_key() -> None:
    assert _verify(jwks=_jwks(_public_jwk(kid="other"), _public_jwk())) is not None


@pytest.mark.parametrize(
    "jwks",
    [
        {"keys": []},
        {"keys": [_public_jwk(kid="unknown")]},
        {"keys": [_public_jwk(), _public_jwk()]},  # duplicate matching kid
        {"keys": [_public_jwk(use="enc")]},
        {"keys": [_public_jwk(key_ops=["encrypt"])]},
        {"keys": [_public_jwk(key_ops="verify")]},  # not a list
        {"keys": [_public_jwk(alg="RS512")]},
        {"keys": ["not-a-mapping"]},
    ],
)
def test_no_single_usable_candidate_is_rejected(jwks: dict[str, Any]) -> None:
    assert _verify(jwks=jwks) is None


def _token_without_kid() -> str:
    return jwt.encode(
        {"iss": ISSUER, "aud": CLIENT_ID, "sub": SUBJECT, "nonce": NONCE,
         "exp": NOW.timestamp() + 300, "iat": NOW.timestamp() - 5},
        _PRIVATE,
        algorithm="RS256",
    )


def test_without_a_kid_exactly_one_candidate_succeeds() -> None:
    key = _public_jwk()
    key.pop("kid")

    assert _verify(id_token=_token_without_kid(), jwks=_jwks(key)) is not None
    # Two usable keys without a kid stay ambiguous and are refused.
    assert _verify(id_token=_token_without_kid(), jwks=_jwks(key, dict(key))) is None


def test_an_empty_kid_header_is_refused() -> None:
    assert _verify(id_token=_token(headers={"kid": ""})) is None


def test_a_malformed_trusted_jwk_is_technically_unavailable() -> None:
    with pytest.raises(OidcVerificationUnavailable):
        _verify(jwks=_jwks({"kty": "RSA", "kid": "key-1", "use": "sig", "alg": "RS256"}))


# --- 6. Signature ----------------------------------------------------------

def test_a_token_signed_with_another_key_is_rejected() -> None:
    assert _verify(id_token=_token(private=_OTHER_PRIVATE)) is None


def test_a_tampered_signature_is_rejected() -> None:
    assert _verify(id_token=_token()[:-6] + "AAAAAA") is None


@pytest.mark.parametrize("token", ["", "not-a-token", "a.b", 42, None])
def test_a_malformed_or_wrong_typed_token_is_rejected(token: Any) -> None:
    assert _verify(id_token=token) is None


# --- 7. Claims -------------------------------------------------------------

@pytest.mark.parametrize(
    "claims",
    [
        {"iss": "https://evil.example.test"},
        {"aud": "other-client"},
        {"aud": []},
        {"aud": [1, CLIENT_ID]},
        {"aud": 7},
        {"aud": ""},
        {"aud": [CLIENT_ID, "second"]},  # several audiences without azp
        {"aud": [CLIENT_ID, "second"], "azp": "other"},
        {"aud": [CLIENT_ID, "second"], "azp": 1},
        {"azp": "other-client"},  # present with one audience, must still match
        {"nonce": "wrong-nonce"},
        {"nonce": ""},
        {"nonce": 1},
        {"sub": ""},
        {"sub": 1},
    ],
)
def test_a_rejected_claim_yields_none(claims: dict[str, Any]) -> None:
    assert _verify(id_token=_token(**claims)) is None


@pytest.mark.parametrize("name", ["aud", "nonce", "sub"])
def test_a_missing_required_claim_yields_none(name: str) -> None:
    assert _verify(id_token=_token(drop=(name,))) is None


def test_several_audiences_with_a_matching_azp_are_accepted() -> None:
    token = _token(aud=[CLIENT_ID, "second"], azp=CLIENT_ID)

    assert _verify(id_token=token) is not None


# --- 8. Time ---------------------------------------------------------------

def test_a_token_just_inside_the_skew_is_still_valid() -> None:
    token = _token(exp=NOW.timestamp() - SKEW.total_seconds() + 1)

    assert _verify(id_token=token) is not None


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": NOW.timestamp() - SKEW.total_seconds()},  # exactly at the edge
        {"exp": NOW.timestamp() - 3600},
        {"nbf": NOW.timestamp() + SKEW.total_seconds() + 1},
        {"iat": NOW.timestamp() + SKEW.total_seconds() + 1},
    ],
)
def test_a_time_claim_outside_the_skew_is_rejected(claims: dict[str, Any]) -> None:
    assert _verify(id_token=_token(**claims)) is None


@pytest.mark.parametrize("name", ["exp", "iat"])
@pytest.mark.parametrize("value", ["1", True, float("inf"), float("nan"), None, [1]])
def test_a_non_numeric_required_time_claim_is_rejected(name: str, value: Any) -> None:
    assert _verify(id_token=_token(**{name: value})) is None


@pytest.mark.parametrize("name", ["exp", "iat"])
def test_a_missing_required_time_claim_is_rejected(name: str) -> None:
    assert _verify(id_token=_token(drop=(name,))) is None


@pytest.mark.parametrize("value", ["1", True, float("inf")])
def test_a_present_but_unusable_nbf_is_rejected(value: Any) -> None:
    assert _verify(id_token=_token(nbf=value)) is None


# --- 9. Technical boundaries -----------------------------------------------

@pytest.mark.parametrize(
    "jwks", [{}, {"keys": None}, {"keys": "not-a-list"}, {"other": []}]
)
def test_a_malformed_jwks_structure_is_technically_unavailable(
    jwks: dict[str, Any],
) -> None:
    with pytest.raises(OidcVerificationUnavailable):
        _verify(jwks=jwks)


def test_an_unexpected_library_fault_is_unavailable_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _explode(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"backend failed for {SUBJECT} nonce {NONCE}")

    monkeypatch.setattr(
        "liquent_platform.identity.oidc_id_token_verifier.jwt.decode", _explode
    )

    with pytest.raises(OidcVerificationUnavailable) as raised:
        _verify()

    rendered = f"{raised.value}{raised.value.args}"
    for secret in (SUBJECT, NONCE, ISSUER, "code-1", "verifier-1"):
        assert secret not in rendered


def test_a_naive_clock_is_a_caller_error_without_token_values() -> None:
    with pytest.raises(ValueError) as raised:
        _verify(now=datetime(2026, 8, 6, 12))

    message = str(raised.value)
    assert "timezone-aware" in message
    for secret in (SUBJECT, NONCE, "code-1"):
        assert secret not in message


def test_the_inputs_are_not_mutated() -> None:
    jwks = _jwks()
    snapshot = json.dumps(jwks, sort_keys=True)

    _verify(jwks=jwks)

    assert json.dumps(jwks, sort_keys=True) == snapshot


# --- 10. Signature ---------------------------------------------------------

def test_signature_has_exactly_the_five_agreed_parameters() -> None:
    assert list(inspect.signature(verify_oidc_id_token).parameters) == [
        "id_token",
        "jwks",
        "configuration",
        "verification",
        "now",
    ]
