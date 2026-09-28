import inspect
from dataclasses import FrozenInstanceError, fields
from typing import Any

import pytest

from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
    OidcVerificationUnavailable,
)


CODE = "authorization-code-1"
ISSUER = "https://idp.example.test"
NONCE = "expected-nonce-1"
VERIFIER = "code-verifier-1"
REDIRECT_URI = "https://app.example.test/v1/session/oidc/callback"

FIELD_NAMES = [
    "authorization_code",
    "expected_issuer",
    "expected_nonce",
    "code_verifier",
    "redirect_uri",
    "expected_trust_revision",
]
REQUIRED_FIELD_NAMES = FIELD_NAMES[:-1]


def _verification(**overrides: Any) -> OidcAuthorizationCodeVerification:
    arguments: dict[str, Any] = {
        "authorization_code": CODE,
        "expected_issuer": ISSUER,
        "expected_nonce": NONCE,
        "code_verifier": VERIFIER,
        "redirect_uri": REDIRECT_URI,
    }
    arguments.update(overrides)
    return OidcAuthorizationCodeVerification(**arguments)


# --- Success ---------------------------------------------------------------

def test_all_five_values_are_preserved_exactly() -> None:
    verification = _verification()

    assert verification.authorization_code == CODE
    assert verification.expected_issuer == ISSUER
    assert verification.expected_nonce == NONCE
    assert verification.code_verifier == VERIFIER
    assert verification.redirect_uri == REDIRECT_URI


def test_model_is_immutable() -> None:
    verification = _verification()

    with pytest.raises(FrozenInstanceError):
        verification.authorization_code = "other"  # type: ignore[misc]


def test_model_uses_slots() -> None:
    assert OidcAuthorizationCodeVerification.__slots__ == tuple(FIELD_NAMES)


def test_model_has_no_instance_dict() -> None:
    assert not hasattr(_verification(), "__dict__")


def test_model_is_hashable_and_usable_as_a_key() -> None:
    assert hash(_verification()) == hash(_verification())
    assert {_verification(): 1}[_verification()] == 1


def test_two_equal_inputs_compare_equal() -> None:
    assert _verification() == _verification()


def test_a_differing_value_makes_two_inputs_unequal() -> None:
    assert _verification() != _verification(authorization_code="other-code")


def test_model_has_exactly_the_revision_bound_fields_in_order() -> None:
    assert [f.name for f in fields(OidcAuthorizationCodeVerification)] == FIELD_NAMES


@pytest.mark.parametrize("name", REQUIRED_FIELD_NAMES)
def test_every_field_is_mandatory(name: str) -> None:
    arguments = {
        "authorization_code": CODE,
        "expected_issuer": ISSUER,
        "expected_nonce": NONCE,
        "code_verifier": VERIFIER,
        "redirect_uri": REDIRECT_URI,
    }
    del arguments[name]

    with pytest.raises(TypeError):
        OidcAuthorizationCodeVerification(**arguments)


# --- Empty values ----------------------------------------------------------

@pytest.mark.parametrize("name", REQUIRED_FIELD_NAMES)
def test_an_empty_value_is_rejected_per_field(name: str) -> None:
    with pytest.raises(ValueError, match=f"{name} must not be empty"):
        _verification(**{name: ""})


def test_the_rejection_message_names_the_field_and_not_the_value() -> None:
    with pytest.raises(ValueError) as raised:
        _verification(authorization_code="")

    message = str(raised.value)
    assert message.startswith("authorization_code")
    # No other configured value leaks into the message either.
    for secret in (CODE, ISSUER, NONCE, VERIFIER, REDIRECT_URI):
        assert secret not in message


# --- Nothing is normalized -------------------------------------------------

@pytest.mark.parametrize("name", FIELD_NAMES)
@pytest.mark.parametrize(
    "raw",
    [
        "  padded  ",
        "MiXeD-CaSe",
        "UPPER_lower-123",
        "a/b/c",
        "trailing/",
        "with space",
        "with\ttab",
        "reserved+/=chars",
        "query?like=1&more=2",
        "percent%2Fencoded",
        "fragment#like",
        "~unreserved.-_",
    ],
)
def test_values_are_kept_exactly_and_opaquely(name: str, raw: str) -> None:
    """No trimming, lowercasing, URL parsing, or percent-decoding."""

    assert getattr(_verification(**{name: raw}), name) == raw


def test_a_redirect_uri_is_not_parsed_or_validated_as_a_url() -> None:
    """The stored value must reach the token endpoint byte for byte."""

    raw = "https://app.example.test/cb?tenant=Acme&x=1"

    assert _verification(redirect_uri=raw).redirect_uri == raw


# --- repr ------------------------------------------------------------------

def test_repr_shows_the_class_name_but_none_of_the_five_values() -> None:
    secrets = {
        "authorization_code": "SECRET-CODE-AAA",
        "expected_issuer": "SECRET-ISSUER-BBB",
        "expected_nonce": "SECRET-NONCE-CCC",
        "code_verifier": "SECRET-VERIFIER-DDD",
        "redirect_uri": "SECRET-REDIRECT-EEE",
    }

    text = repr(_verification(**secrets))

    assert "OidcAuthorizationCodeVerification" in text
    for value in secrets.values():
        assert value not in text


def test_repr_is_exactly_the_empty_class_form() -> None:
    assert repr(_verification()) == "OidcAuthorizationCodeVerification()"


@pytest.mark.parametrize("name", FIELD_NAMES)
def test_every_field_is_declared_repr_false(name: str) -> None:
    field = next(f for f in fields(OidcAuthorizationCodeVerification) if f.name == name)

    assert field.repr is False


# --- Structural boundaries -------------------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        "state",
        "login_state",
        "admission_id",
        "return_path",
        "configuration",
        "client_configuration",
        "token_endpoint",
        "jwks_uri",
        "allowed_signing_algorithms",
        "clock_skew",
        "client_id",
        "client_secret",
        "id_token",
        "access_token",
        "refresh_token",
        "token",
        "claims",
        "subject",
        "sub",
        "identity",
        "external_identity",
        "user_id",
        "workspace_id",
        "role",
        "session",
        "session_id",
        "csrf",
        "now",
        "clock",
    ],
)
def test_model_carries_no_forbidden_field(name: str) -> None:
    assert not hasattr(_verification(), name)
    assert name not in {f.name for f in fields(OidcAuthorizationCodeVerification)}


# --- OidcVerificationUnavailable -------------------------------------------

def test_error_code_is_the_neutral_constant() -> None:
    assert OidcVerificationUnavailable.code == "oidc_verification_unavailable"


def test_error_message_is_exactly_the_neutral_code() -> None:
    assert str(OidcVerificationUnavailable()) == "oidc_verification_unavailable"


def test_error_args_carry_only_the_neutral_code() -> None:
    assert OidcVerificationUnavailable().args == ("oidc_verification_unavailable",)


def test_error_takes_no_detail_argument() -> None:
    with pytest.raises(TypeError):
        OidcVerificationUnavailable("token endpoint at idp.example.test refused")  # type: ignore[call-arg]


def test_error_constructor_accepts_only_self() -> None:
    parameters = inspect.signature(OidcVerificationUnavailable.__init__).parameters

    assert list(parameters) == ["self"]


def test_error_is_an_exception_and_not_a_value_error() -> None:
    error = OidcVerificationUnavailable()

    assert isinstance(error, Exception)
    assert not isinstance(error, ValueError)


@pytest.mark.parametrize(
    "name",
    [
        "authorization_code",
        "code",  # the class attribute is the neutral string, checked separately
        "state",
        "nonce",
        "code_verifier",
        "issuer",
        "redirect_uri",
        "token",
        "id_token",
        "claims",
        "provider",
        "detail",
        "reason",
        "configuration",
    ],
)
def test_error_instance_carries_no_sensitive_attribute(name: str) -> None:
    error = OidcVerificationUnavailable()

    if name == "code":
        # Present on purpose, and it is the neutral code and nothing else.
        assert error.code == "oidc_verification_unavailable"
    else:
        assert not hasattr(error, name)


def test_raising_the_error_never_reveals_a_cause_value() -> None:
    secret = "authorization-code-that-must-not-leak"

    with pytest.raises(OidcVerificationUnavailable) as raised:
        try:
            raise RuntimeError(f"token endpoint refused {secret}")
        except RuntimeError:
            raise OidcVerificationUnavailable from None

    assert secret not in str(raised.value)
    assert raised.value.args == ("oidc_verification_unavailable",)
