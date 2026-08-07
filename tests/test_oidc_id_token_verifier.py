import inspect
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, rsa
from jwt.algorithms import ECAlgorithm, OKPAlgorithm, RSAAlgorithm

from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_id_token_verifier import (
    _REFRESHABLE_KEY_MISS,
    _REJECTED,
    _OidcIdTokenVerificationResult,
    _verify_oidc_id_token_for_adapter,
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
SKEW_SECONDS = 30.0

# Locally generated key material only: no network and no real provider.
_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_EC_P256 = ec.generate_private_key(ec.SECP256R1())
_EC_P384 = ec.generate_private_key(ec.SECP384R1())
_ED25519 = ed25519.Ed25519PrivateKey.generate()
_ED448 = ed448.Ed448PrivateKey.generate()


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
        "clock_skew": timedelta(seconds=SKEW_SECONDS),
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
    headers = {"kid": "key-1", **(headers or {})} if headers != {} else {}
    return jwt.encode(payload, private, algorithm=algorithm, headers=headers)


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


# --- Success and trust snapshot --------------------------------------------

def test_a_valid_token_yields_the_configured_issuer_and_its_subject() -> None:
    assert _verify() == ExternalIdentity(issuer=ISSUER, subject=SUBJECT)


def test_a_configuration_issuer_differing_from_the_expectation_is_rejected() -> None:
    assert _verify(verification=_verification(expected_issuer="https://other.test")) is None


# --- Algorithm boundary ----------------------------------------------------

def test_an_algorithm_outside_the_configured_allowlist_is_rejected() -> None:
    assert _verify(configuration=_configuration(allowed_signing_algorithms=("ES256",))) is None


def test_a_symmetric_algorithm_is_refused_even_when_configured() -> None:
    """The JWK carries no ``alg``, so only the internal allowlist can reject."""

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


def test_an_unsigned_token_is_rejected_and_cannot_even_be_configured() -> None:
    token = jwt.encode(
        {"iss": ISSUER, "aud": CLIENT_ID, "sub": SUBJECT, "nonce": NONCE,
         "exp": NOW.timestamp() + 300, "iat": NOW.timestamp() - 5},
        key=None,
        algorithm=None,
        headers={"kid": "key-1"},
    )

    assert _verify(id_token=token) is None
    with pytest.raises(ValueError):  # LQ-156 already refuses "none"
        _configuration(allowed_signing_algorithms=("RS256", "none"))


# --- Token-controlled key sources ------------------------------------------

@pytest.mark.parametrize("name", ["jku", "x5u", "jwk"])
def test_a_token_controlled_key_source_is_refused(name: str) -> None:
    value = _public_jwk() if name == "jwk" else "https://evil.example.test/keys"

    assert _verify(id_token=_token(headers={name: value})) is None


# --- Key selection ---------------------------------------------------------

def test_a_unique_kid_selects_its_key_among_others() -> None:
    assert _verify(jwks=_jwks(_public_jwk(kid="other"), _public_jwk())) is not None


@pytest.mark.parametrize(
    "jwks",
    [
        {"keys": [_public_jwk(kid="unknown")]},
        {"keys": [_public_jwk(), _public_jwk()]},  # ambiguous kid
        {"keys": [_public_jwk(use="enc")]},
        {"keys": [_public_jwk(key_ops=["encrypt"])]},
        {"keys": [_public_jwk(alg="RS512")]},
        {"keys": ["not-a-mapping"]},
    ],
)
def test_no_single_usable_candidate_is_rejected(jwks: dict[str, Any]) -> None:
    assert _verify(jwks=jwks) is None


def test_an_empty_kid_header_is_refused_even_if_a_key_carries_one() -> None:
    """An empty kid must be refused outright, not matched against the set."""

    assert _verify(
        id_token=_token(headers={"kid": ""}), jwks=_jwks(_public_jwk(kid=""))
    ) is None


def test_without_a_kid_exactly_one_candidate_is_required() -> None:
    key = _public_jwk()
    key.pop("kid")
    token = _token(headers={})

    assert _verify(id_token=token, jwks=_jwks(key)) is not None
    assert _verify(id_token=token, jwks=_jwks(key, dict(key))) is None


def test_a_malformed_trusted_jwk_is_technically_unavailable() -> None:
    with pytest.raises(OidcVerificationUnavailable):
        _verify(jwks=_jwks({"kty": "RSA", "kid": "key-1", "use": "sig", "alg": "RS256"}))


# --- Key family and curve must match the algorithm -------------------------

def _asymmetric_token(private: Any, algorithm: str) -> str:
    return jwt.encode(
        {"iss": ISSUER, "aud": CLIENT_ID, "sub": SUBJECT, "nonce": NONCE,
         "exp": NOW.timestamp() + 300, "iat": NOW.timestamp() - 5},
        private,
        algorithm=algorithm,
        headers={"kid": "key-1"},
    )


def _jwk_for(private: Any, algorithm: Any, **overrides: Any) -> dict[str, Any]:
    """A trusted JWK for the given key, deliberately without its own ``alg``."""

    jwk = json.loads(algorithm.to_jwk(private.public_key()))
    jwk.pop("alg", None)
    jwk.update(kid="key-1", use="sig")
    jwk.update(overrides)
    return jwk


@pytest.mark.parametrize(
    ("algorithm", "signer", "jwk"),
    [
        # An allowed algorithm the trusted set cannot serve is a rejection,
        # never a technical failure.
        ("ES256", _EC_P256, _jwk_for(_PRIVATE, RSAAlgorithm)),
        ("RS256", _PRIVATE, _jwk_for(_EC_P256, ECAlgorithm)),
        ("ES256", _EC_P256, _jwk_for(_EC_P384, ECAlgorithm)),  # wrong curve
        ("EdDSA", _ED25519, _jwk_for(_ED448, OKPAlgorithm)),  # unsuitable curve
    ],
)
def test_a_key_of_the_wrong_family_or_curve_is_rejected(
    algorithm: str, signer: Any, jwk: dict[str, Any]
) -> None:
    result = _verify(
        id_token=_asymmetric_token(signer, algorithm),
        jwks=_jwks(jwk),
        configuration=_configuration(
            allowed_signing_algorithms=("RS256", "ES256", "EdDSA")
        ),
    )

    assert result is None


@pytest.mark.parametrize(
    "jwk",
    [
        _jwk_for(_PRIVATE, RSAAlgorithm, kty=None),
        _jwk_for(_PRIVATE, RSAAlgorithm, kty=7),
        _jwk_for(_EC_P256, ECAlgorithm, crv=None),
        _jwk_for(_EC_P256, ECAlgorithm, crv=7),
    ],
)
def test_an_unreadable_key_family_or_curve_is_technically_unavailable(
    jwk: dict[str, Any],
) -> None:
    algorithm = "RS256" if jwk.get("kty") in (None, 7) else "ES256"

    with pytest.raises(OidcVerificationUnavailable):
        _verify(
            id_token=_asymmetric_token(
                _PRIVATE if algorithm == "RS256" else _EC_P256, algorithm
            ),
            jwks=_jwks(jwk),
            configuration=_configuration(
                allowed_signing_algorithms=("RS256", "ES256")
            ),
        )


def test_a_matching_ec_key_still_verifies() -> None:
    result = _verify(
        id_token=_asymmetric_token(_EC_P256, "ES256"),
        jwks=_jwks(_jwk_for(_EC_P256, ECAlgorithm)),
        configuration=_configuration(allowed_signing_algorithms=("ES256",)),
    )

    assert result == ExternalIdentity(issuer=ISSUER, subject=SUBJECT)


# --- Signature -------------------------------------------------------------

def test_a_token_signed_with_another_key_is_rejected() -> None:
    assert _verify(id_token=_token(private=_OTHER_PRIVATE)) is None


@pytest.mark.parametrize("token", ["not-a-token", 42, _token()[:-6] + "AAAAAA"])
def test_a_tampered_or_malformed_token_is_rejected(token: Any) -> None:
    assert _verify(id_token=token) is None


# --- Claims ----------------------------------------------------------------

@pytest.mark.parametrize(
    "claims",
    [
        {"iss": "https://evil.example.test"},
        {"aud": "other-client"},
        {"aud": [1, CLIENT_ID]},
        {"aud": [CLIENT_ID, "second"]},  # several audiences without azp
        {"aud": [CLIENT_ID, "second"], "azp": "other"},
        {"azp": "other-client"},  # present with one audience, must still match
        {"nonce": "wrong-nonce"},
        {"sub": ""},
    ],
)
def test_a_rejected_claim_yields_none(claims: dict[str, Any]) -> None:
    assert _verify(id_token=_token(**claims)) is None


@pytest.mark.parametrize("name", ["aud", "nonce", "sub"])
def test_a_missing_required_claim_yields_none(name: str) -> None:
    assert _verify(id_token=_token(drop=(name,))) is None


def test_several_audiences_with_a_matching_azp_are_accepted() -> None:
    assert _verify(id_token=_token(aud=[CLIENT_ID, "second"], azp=CLIENT_ID)) is not None


# --- Time ------------------------------------------------------------------

def test_a_token_just_inside_the_skew_is_still_valid() -> None:
    assert _verify(id_token=_token(exp=NOW.timestamp() - SKEW_SECONDS + 1)) is not None


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": NOW.timestamp() - SKEW_SECONDS},  # exactly at the edge
        {"nbf": NOW.timestamp() + SKEW_SECONDS + 1},
        {"iat": NOW.timestamp() + SKEW_SECONDS + 1},
    ],
)
def test_a_time_claim_outside_the_skew_is_rejected(claims: dict[str, Any]) -> None:
    assert _verify(id_token=_token(**claims)) is None


@pytest.mark.parametrize(
    ("name", "value"),
    [("exp", True), ("iat", "1"), ("nbf", float("inf"))],  # bool, type, non-finite
)
def test_an_unusable_time_value_is_rejected(name: str, value: Any) -> None:
    assert _verify(id_token=_token(**{name: value})) is None


@pytest.mark.parametrize("name", ["exp", "iat"])
def test_a_missing_required_time_claim_is_rejected(name: str) -> None:
    assert _verify(id_token=_token(drop=(name,))) is None


# --- Technical boundaries --------------------------------------------------

@pytest.mark.parametrize("jwks", [{}, {"keys": "not-a-list"}])
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
    assert all(secret not in rendered for secret in (SUBJECT, NONCE, ISSUER))


def test_a_naive_clock_is_a_caller_error_without_token_values() -> None:
    with pytest.raises(ValueError) as raised:
        _verify(now=datetime(2026, 8, 6, 12))

    message = str(raised.value)
    assert "timezone-aware" in message
    assert all(secret not in message for secret in (SUBJECT, NONCE, "code-1"))


def test_signature_has_exactly_the_five_agreed_parameters() -> None:
    assert list(inspect.signature(verify_oidc_id_token).parameters) == [
        "id_token",
        "jwks",
        "configuration",
        "verification",
        "now",
    ]


# --- LQ-169: the private outcome that keeps the refresh hint ----------------

def _outcome(**overrides: Any) -> _OidcIdTokenVerificationResult:
    arguments: dict[str, Any] = {
        "id_token": _token(),
        "jwks": _jwks(),
        "configuration": _configuration(),
        "verification": _verification(),
        "now": NOW,
    }
    arguments.update(overrides)
    return _verify_oidc_id_token_for_adapter(**arguments)


def test_the_private_outcome_has_exactly_three_states() -> None:
    identity = ExternalIdentity(issuer=ISSUER, subject=SUBJECT)
    verified = _OidcIdTokenVerificationResult(
        identity=identity, refreshable_key_miss=False
    )

    assert (verified.identity, verified.refreshable_key_miss) == (identity, False)
    assert (_REJECTED.identity, _REJECTED.refreshable_key_miss) == (None, False)
    assert (_REFRESHABLE_KEY_MISS.identity, _REFRESHABLE_KEY_MISS.refreshable_key_miss) == (
        None,
        True,
    )
    # Neither field reaches the representation.
    assert repr(verified) == "_OidcIdTokenVerificationResult()"

    with pytest.raises(ValueError, match="never a refreshable key miss") as raised:
        _OidcIdTokenVerificationResult(identity=identity, refreshable_key_miss=True)
    assert all(secret not in str(raised.value) for secret in (SUBJECT, ISSUER))


@pytest.mark.parametrize(
    "jwks",
    [_jwks(_public_jwk(kid="rotated-away")), {"keys": []}],
    ids=["other-kid-only", "readable-but-empty"],
)
def test_a_provably_absent_kid_is_a_refreshable_miss(jwks: dict[str, Any]) -> None:
    result = _outcome(jwks=jwks)

    assert result.refreshable_key_miss is True
    assert result.identity is None
    # The public contract still cannot tell this from any other rejection.
    assert _verify(jwks=jwks) is None


@pytest.mark.parametrize(
    "jwks",
    [
        _jwks(_public_jwk(use="enc")),
        _jwks(_public_jwk(), _public_jwk()),
        _jwks(_jwk_for(_EC_P256, ECAlgorithm)),
        {"keys": [_public_jwk(kid="rotated-away"), "not-a-mapping"]},
    ],
    ids=["unsuitable-use", "duplicate-kid", "incompatible-family", "unreadable-entry"],
)
def test_a_present_or_unreadable_key_set_is_never_a_refreshable_miss(
    jwks: dict[str, Any],
) -> None:
    result = _outcome(jwks=jwks)

    assert result.refreshable_key_miss is False
    assert result.identity is None
    assert _verify(jwks=jwks) is None


@pytest.mark.parametrize(
    ("headers", "jwks"),
    [
        # Without a kid the token names nothing to look up, so an ambiguous set
        # is a definitive rejection rather than something a reload could fix.
        ({}, _jwks(_public_jwk(), _public_jwk(kid="other"))),
        ({"kid": ""}, _jwks(_public_jwk(kid="rotated-away"))),
    ],
    ids=["kid-absent", "kid-empty"],
)
def test_an_unusable_token_kid_is_never_a_refreshable_miss(
    headers: dict[str, Any], jwks: dict[str, Any]
) -> None:
    """A non-string kid is unreachable here: PyJWT refuses to encode one."""

    result = _outcome(id_token=_token(headers=headers), jwks=jwks)

    assert result.refreshable_key_miss is False
    assert result.identity is None


@pytest.mark.parametrize(
    ("headers", "configuration"),
    [
        ({"jku": "https://evil.test/keys"}, _configuration()),
        ({}, _configuration(allowed_signing_algorithms=("ES256",))),
    ],
    ids=["token-controlled-source", "algorithm-not-allowed"],
)
def test_a_refused_key_source_or_algorithm_is_never_a_refreshable_miss(
    headers: dict[str, Any], configuration: TrustedOidcClientConfiguration
) -> None:
    result = _outcome(
        id_token=_token(headers={"kid": "rotated-away", **headers}),
        jwks=_jwks(),
        configuration=configuration,
    )

    assert result.refreshable_key_miss is False
    assert result.identity is None
