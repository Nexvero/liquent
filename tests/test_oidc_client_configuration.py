from dataclasses import MISSING, FrozenInstanceError, fields
from datetime import timedelta
from typing import Any

import pytest

from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)


ISSUER = "https://idp.example.test"
AUTHORIZATION_ENDPOINT = "https://idp.example.test/authorize"
CLIENT_ID = "liquent-control-plane"
REDIRECT_URI = "https://app.example.test/v1/oidc/callback"
SCOPES = ("openid",)
TOKEN_ENDPOINT = "https://idp.example.test/token"
JWKS_URI = "https://idp.example.test/jwks"
ALGORITHMS = ("RS256",)
CLOCK_SKEW = timedelta(seconds=30)


def _configuration(**overrides: Any) -> TrustedOidcClientConfiguration:
    arguments: dict[str, Any] = {
        "issuer": ISSUER,
        "authorization_endpoint": AUTHORIZATION_ENDPOINT,
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scopes": SCOPES,
        "token_endpoint": TOKEN_ENDPOINT,
        "jwks_uri": JWKS_URI,
        "allowed_signing_algorithms": ALGORITHMS,
        "clock_skew": CLOCK_SKEW,
    }
    arguments.update(overrides)
    return TrustedOidcClientConfiguration(**arguments)


# --- Success --------------------------------------------------------------

def test_valid_configuration_is_accepted() -> None:
    configuration = _configuration()

    assert configuration.issuer == ISSUER
    assert configuration.authorization_endpoint == AUTHORIZATION_ENDPOINT
    assert configuration.client_id == CLIENT_ID
    assert configuration.redirect_uri == REDIRECT_URI
    assert configuration.scopes == SCOPES
    assert configuration.token_endpoint == TOKEN_ENDPOINT
    assert configuration.jwks_uri == JWKS_URI
    assert configuration.allowed_signing_algorithms == ALGORITHMS
    assert configuration.clock_skew == CLOCK_SKEW


def test_model_is_immutable() -> None:
    configuration = _configuration()

    with pytest.raises(FrozenInstanceError):
        configuration.client_id = "other"  # type: ignore[misc]


def test_model_is_hashable() -> None:
    assert hash(_configuration()) == hash(_configuration())


def test_model_has_exactly_the_nine_agreed_fields_in_order() -> None:
    names = [field.name for field in fields(TrustedOidcClientConfiguration)]

    assert names == [
        "issuer",
        "authorization_endpoint",
        "client_id",
        "redirect_uri",
        "scopes",
        "token_endpoint",
        "jwks_uri",
        "allowed_signing_algorithms",
        "clock_skew",
    ]


def test_model_uses_slots() -> None:
    assert TrustedOidcClientConfiguration.__slots__ == (
        "issuer",
        "authorization_endpoint",
        "client_id",
        "redirect_uri",
        "scopes",
        "token_endpoint",
        "jwks_uri",
        "allowed_signing_algorithms",
        "clock_skew",
    )


NEW_REQUIRED_FIELDS = [
    "token_endpoint",
    "jwks_uri",
    "allowed_signing_algorithms",
    "clock_skew",
]


@pytest.mark.parametrize("name", NEW_REQUIRED_FIELDS)
def test_the_new_fields_have_no_default(name: str) -> None:
    """Every verification value must be stated explicitly at build time."""

    arguments = {
        "issuer": ISSUER,
        "authorization_endpoint": AUTHORIZATION_ENDPOINT,
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scopes": SCOPES,
        "token_endpoint": TOKEN_ENDPOINT,
        "jwks_uri": JWKS_URI,
        "allowed_signing_algorithms": ALGORITHMS,
        "clock_skew": CLOCK_SKEW,
    }
    del arguments[name]

    with pytest.raises(TypeError):
        TrustedOidcClientConfiguration(**arguments)


@pytest.mark.parametrize("name", NEW_REQUIRED_FIELDS)
def test_no_dataclass_default_is_declared_for_the_new_fields(name: str) -> None:
    field = next(f for f in fields(TrustedOidcClientConfiguration) if f.name == name)

    assert field.default is MISSING
    assert field.default_factory is MISSING


def test_issuer_path_and_trailing_slash_are_kept_verbatim() -> None:
    raw = "https://idp.example.test:8443/Tenant/Realm/"

    assert _configuration(issuer=raw).issuer == raw


def test_authorization_endpoint_path_and_port_are_accepted_verbatim() -> None:
    raw = "https://idp.example.test:8443/Oauth2/Authorize"

    assert _configuration(authorization_endpoint=raw).authorization_endpoint == raw


def test_redirect_uri_with_a_configured_query_is_kept_verbatim() -> None:
    raw = "https://app.example.test/v1/oidc/callback?tenant=Acme"

    assert _configuration(redirect_uri=raw).redirect_uri == raw


def test_scope_order_is_preserved_exactly() -> None:
    scopes = ("email", "openid", "profile")

    assert _configuration(scopes=scopes).scopes == scopes


# --- Issuer ---------------------------------------------------------------

@pytest.mark.parametrize(
    ("issuer", "message"),
    [
        ("", "issuer must not be empty"),
        ("http://idp.example.test", "issuer must be an absolute https url"),
        ("/authorize", "issuer must be an absolute https url"),
        ("https:///path", "issuer must have a host"),
        ("https://user:pw@idp.example.test", "issuer must not contain userinfo"),
        ("https://idp.example.test?a=b", "issuer must not contain a query"),
        ("https://idp.example.test#frag", "issuer must not contain a fragment"),
    ],
)
def test_invalid_issuer_is_rejected(issuer: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _configuration(issuer=issuer)


# --- Authorization endpoint -----------------------------------------------

@pytest.mark.parametrize(
    ("endpoint", "message"),
    [
        ("", "authorization_endpoint must not be empty"),
        ("http://idp.example.test/authorize", "must be an absolute https url"),
        ("/authorize", "must be an absolute https url"),
        ("https:///authorize", "authorization_endpoint must have a host"),
        ("https://user@idp.example.test/authorize", "must not contain userinfo"),
        ("https://idp.example.test/authorize?a=b", "must not contain a query"),
        ("https://idp.example.test/authorize#f", "must not contain a fragment"),
    ],
)
def test_invalid_authorization_endpoint_is_rejected(
    endpoint: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _configuration(authorization_endpoint=endpoint)


# --- Client id ------------------------------------------------------------

def test_empty_client_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="client_id must not be empty"):
        _configuration(client_id="")


def test_client_id_is_kept_exactly_and_not_normalized() -> None:
    raw = "  Liquent/Client ID  "

    assert _configuration(client_id=raw).client_id == raw


# --- Redirect uri ---------------------------------------------------------

@pytest.mark.parametrize(
    ("redirect_uri", "message"),
    [
        ("", "redirect_uri must not be empty"),
        ("http://app.example.test/cb", "redirect_uri must be an absolute https url"),
        ("/v1/oidc/callback", "redirect_uri must be an absolute https url"),
        ("https:///cb", "redirect_uri must have a host"),
        ("https://user@app.example.test/cb", "redirect_uri must not contain userinfo"),
        ("https://app.example.test/cb#frag", "redirect_uri must not contain a fragment"),
    ],
)
def test_invalid_redirect_uri_is_rejected(redirect_uri: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _configuration(redirect_uri=redirect_uri)


def test_redirect_uri_is_not_derived_from_issuer_or_endpoint() -> None:
    # A redirect URI on a completely different host stays exactly as configured.
    configuration = _configuration(redirect_uri="https://other.example.test/cb")

    assert configuration.redirect_uri == "https://other.example.test/cb"
    assert configuration.issuer == ISSUER
    assert configuration.authorization_endpoint == AUTHORIZATION_ENDPOINT


# --- URL syntax hardening, all three URL fields ----------------------------

URL_FIELDS = ["issuer", "authorization_endpoint", "redirect_uri"]


@pytest.mark.parametrize("field", URL_FIELDS)
@pytest.mark.parametrize(
    "raw",
    [
        "https://idp.example.test/a b",
        "https://idp.example.test/a\tb",
        "https://idp.example.test/a\nb",
        "https://idp.example.test/a\rb",
        # urlsplit strips this newline and would report the clean host, while
        # the unsafe original string is what the model would store.
        "https://idp.example\n.test/a",
    ],
)
def test_raw_whitespace_or_control_characters_are_rejected(
    field: str, raw: str
) -> None:
    with pytest.raises(ValueError, match="must not contain whitespace or control"):
        _configuration(**{field: raw})


@pytest.mark.parametrize("field", URL_FIELDS)
@pytest.mark.parametrize(
    "raw",
    [
        "https://idp.example.test:notaport/a",
        "https://idp.example.test:65536/a",
    ],
)
def test_invalid_port_is_rejected(field: str, raw: str) -> None:
    with pytest.raises(ValueError, match="must have a valid port"):
        _configuration(**{field: raw})


@pytest.mark.parametrize("field", URL_FIELDS)
def test_valid_explicit_port_is_accepted_and_kept_verbatim(field: str) -> None:
    raw = "https://idp.example.test:8443/a"

    assert getattr(_configuration(**{field: raw}), field) == raw


@pytest.mark.parametrize("field", ["issuer", "authorization_endpoint"])
def test_empty_query_separator_is_rejected_for_issuer_and_endpoint(
    field: str,
) -> None:
    with pytest.raises(ValueError, match="must not contain a query"):
        _configuration(**{field: "https://idp.example.test/authorize?"})


@pytest.mark.parametrize("field", URL_FIELDS)
def test_empty_fragment_separator_is_always_rejected(field: str) -> None:
    with pytest.raises(ValueError, match="must not contain a fragment"):
        _configuration(**{field: "https://idp.example.test/authorize#"})


def test_empty_query_separator_stays_allowed_and_exact_for_redirect_uri() -> None:
    raw = "https://app.example.test/v1/oidc/callback?"

    assert _configuration(redirect_uri=raw).redirect_uri == raw


@pytest.mark.parametrize(
    ("field", "raw"),
    [
        ("issuer", "https://idp.example.test:notaport/private-tenant"),
        ("authorization_endpoint", "https://idp.example.test/authorize?leak=1"),
        ("redirect_uri", "https://app.example.test/cb#leak"),
    ],
)
def test_rejected_url_never_appears_in_the_error_message(
    field: str, raw: str
) -> None:
    with pytest.raises(ValueError) as raised:
        _configuration(**{field: raw})

    message = str(raised.value)
    assert message.startswith(field)
    for secret in (raw, "idp.example.test", "app.example.test", "notaport", "leak"):
        assert secret not in message


# --- Scopes ---------------------------------------------------------------

@pytest.mark.parametrize(
    ("scopes", "message"),
    [
        ((), "scopes must not be empty"),
        (("email",), "scopes must contain openid"),
        (("openid", ""), "scope must not be empty"),
        (("openid", "email", "email"), "scopes must not repeat"),
        (("openid", "read write"), "scope must not contain whitespace"),
        (("openid", "read\twrite"), "scope must not contain whitespace"),
        (("openid", "read\nwrite"), "scope must not contain whitespace"),
        (["openid"], "scopes must be a tuple"),
        (("openid", 1), "each scope must be a string"),
    ],
)
def test_invalid_scopes_are_rejected(scopes: Any, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _configuration(scopes=scopes)


def test_standard_scopes_are_kept_only_when_configured() -> None:
    only_openid = _configuration()
    with_extras = _configuration(scopes=("openid", "email", "profile"))

    assert only_openid.scopes == ("openid",)
    assert with_extras.scopes == ("openid", "email", "profile")


def test_offline_access_is_never_added_automatically() -> None:
    assert "offline_access" not in _configuration().scopes
    assert "offline_access" not in _configuration(
        scopes=("openid", "email")
    ).scopes


# --- Token endpoint and JWKS URI (LQ-156) ----------------------------------

VERIFICATION_URL_FIELDS = ["token_endpoint", "jwks_uri"]


@pytest.mark.parametrize("field", VERIFICATION_URL_FIELDS)
def test_verification_url_with_a_path_is_accepted_and_kept_verbatim(
    field: str,
) -> None:
    raw = "https://idp.example.test/oauth2/v2/Keys"

    assert getattr(_configuration(**{field: raw}), field) == raw


@pytest.mark.parametrize("field", VERIFICATION_URL_FIELDS)
def test_verification_url_with_an_explicit_port_is_kept_verbatim(field: str) -> None:
    raw = "https://idp.example.test:8443/oauth2/token"

    assert getattr(_configuration(**{field: raw}), field) == raw


@pytest.mark.parametrize("field", VERIFICATION_URL_FIELDS)
@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("", "must not be empty"),
        ("http://idp.example.test/token", "must be an absolute https url"),
        ("/token", "must be an absolute https url"),
        ("idp.example.test/token", "must be an absolute https url"),
        ("https:///token", "must have a host"),
        ("https://user@idp.example.test/token", "must not contain userinfo"),
        ("https://user:pw@idp.example.test/token", "must not contain userinfo"),
        ("https://@idp.example.test/token", "must not contain userinfo"),
        ("https://idp.example.test/token?a=b", "must not contain a query"),
        ("https://idp.example.test/token?", "must not contain a query"),
        ("https://idp.example.test/token#frag", "must not contain a fragment"),
        ("https://idp.example.test/token#", "must not contain a fragment"),
        ("https://idp.example.test:notaport/token", "must have a valid port"),
        ("https://idp.example.test:65536/token", "must have a valid port"),
    ],
)
def test_invalid_verification_url_is_rejected(
    field: str, raw: str, reason: str
) -> None:
    with pytest.raises(ValueError, match=f"{field} {reason}"):
        _configuration(**{field: raw})


@pytest.mark.parametrize("field", VERIFICATION_URL_FIELDS)
@pytest.mark.parametrize(
    "raw",
    [
        "https://idp.example.test/to ken",
        "https://idp.example.test/to\tken",
        "https://idp.example.test/to\nken",
        "https://idp.example.test/to\rken",
        # urlsplit strips this newline and would report the clean host, while
        # the unsafe original string is what the model would store.
        "https://idp.example\n.test/token",
    ],
)
def test_verification_url_with_whitespace_or_control_characters_is_rejected(
    field: str, raw: str
) -> None:
    with pytest.raises(ValueError, match="must not contain whitespace or control"):
        _configuration(**{field: raw})


@pytest.mark.parametrize(
    ("field", "raw"),
    [
        ("token_endpoint", "https://secret-idp.example.test:notaport/private"),
        ("jwks_uri", "https://secret-idp.example.test/keys?leak=1"),
    ],
)
def test_rejected_verification_url_never_appears_in_the_error_message(
    field: str, raw: str
) -> None:
    with pytest.raises(ValueError) as raised:
        _configuration(**{field: raw})

    message = str(raised.value)
    assert message.startswith(field)
    for secret in (raw, "secret-idp.example.test", "notaport", "private", "leak"):
        assert secret not in message


def test_verification_urls_are_not_derived_from_issuer_or_endpoint() -> None:
    """Both may live on deliberately different hosts and stay exact."""

    configuration = _configuration(
        token_endpoint="https://tokens.other.example.test:9443/oauth2/token",
        jwks_uri="https://keys.third.example.test/.well-known/jwks.json",
    )

    assert configuration.token_endpoint == (
        "https://tokens.other.example.test:9443/oauth2/token"
    )
    assert configuration.jwks_uri == (
        "https://keys.third.example.test/.well-known/jwks.json"
    )
    # The issuer and authorization endpoint stay untouched by either value.
    assert configuration.issuer == ISSUER
    assert configuration.authorization_endpoint == AUTHORIZATION_ENDPOINT


def test_a_bare_issuer_never_gains_a_token_or_jwks_path() -> None:
    configuration = _configuration()

    assert configuration.token_endpoint != configuration.issuer
    assert configuration.jwks_uri != configuration.issuer
    assert not configuration.token_endpoint.startswith(
        configuration.authorization_endpoint
    )


# --- Allowed signing algorithms (LQ-156) -----------------------------------

def test_algorithm_order_is_preserved_exactly() -> None:
    algorithms = ("PS256", "RS256", "ES256")

    assert (
        _configuration(allowed_signing_algorithms=algorithms).allowed_signing_algorithms
        == algorithms
    )


def test_algorithms_are_not_sorted() -> None:
    algorithms = ("RS512", "ES256", "PS384")

    stored = _configuration(
        allowed_signing_algorithms=algorithms
    ).allowed_signing_algorithms

    assert stored == algorithms
    assert list(stored) != sorted(stored)


def test_no_algorithm_is_added_automatically() -> None:
    stored = _configuration(
        allowed_signing_algorithms=("ES256",)
    ).allowed_signing_algorithms

    assert stored == ("ES256",)
    assert "RS256" not in stored


@pytest.mark.parametrize(
    ("algorithms", "message"),
    [
        ((), "allowed_signing_algorithms must not be empty"),
        (["RS256"], "allowed_signing_algorithms must be a tuple"),
        ("RS256", "allowed_signing_algorithms must be a tuple"),
        (("RS256", 256), "each signing algorithm must be a string"),
        (("RS256", None), "each signing algorithm must be a string"),
        (("RS256", ""), "signing algorithm must not be empty"),
        (("RS256", "RS 256"), "signing algorithm must not contain whitespace"),
        (("RS256", "RS\t256"), "signing algorithm must not contain whitespace"),
        (("RS256", "RS\n256"), "signing algorithm must not contain whitespace"),
        (("RS256", " RS256"), "signing algorithm must not contain whitespace"),
        (("RS256", "RS256"), "allowed_signing_algorithms must not repeat"),
    ],
)
def test_invalid_algorithms_are_rejected(algorithms: Any, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _configuration(allowed_signing_algorithms=algorithms)


@pytest.mark.parametrize(
    "spelling", ["none", "NONE", "None", "nOnE", "nonE", "NoNe"]
)
def test_the_unsigned_algorithm_is_rejected_in_any_spelling(spelling: str) -> None:
    """alg=none would turn every signature check into a no-op."""

    with pytest.raises(ValueError, match="signing algorithm none is not allowed"):
        _configuration(allowed_signing_algorithms=("RS256", spelling))


@pytest.mark.parametrize("spelling", ["none", "NONE"])
def test_the_unsigned_algorithm_is_rejected_even_as_the_only_entry(
    spelling: str,
) -> None:
    with pytest.raises(ValueError, match="signing algorithm none is not allowed"):
        _configuration(allowed_signing_algorithms=(spelling,))


def test_an_algorithm_merely_containing_none_stays_allowed() -> None:
    """The refusal targets the exact alg value, not a substring."""

    algorithms = ("RS256", "none-like", "NONEXISTENT")

    assert (
        _configuration(allowed_signing_algorithms=algorithms).allowed_signing_algorithms
        == algorithms
    )


def test_algorithm_spelling_is_kept_exactly_and_not_normalized() -> None:
    algorithms = ("rs256", "Es384")

    assert (
        _configuration(allowed_signing_algorithms=algorithms).allowed_signing_algorithms
        == algorithms
    )


# --- Clock skew (LQ-156) ---------------------------------------------------

@pytest.mark.parametrize(
    "skew",
    [
        timedelta(0),
        timedelta(seconds=1),
        timedelta(seconds=30),
        timedelta(minutes=1),
        timedelta(minutes=5),  # exactly the bound
        timedelta(milliseconds=250),
    ],
)
def test_accepted_clock_skew_is_kept_exactly(skew: timedelta) -> None:
    assert _configuration(clock_skew=skew).clock_skew == skew


def test_sub_second_clock_skew_is_not_rounded() -> None:
    skew = timedelta(seconds=1, microseconds=1)

    stored = _configuration(clock_skew=skew).clock_skew

    assert stored == skew
    assert stored.microseconds == 1


@pytest.mark.parametrize(
    "skew",
    [
        timedelta(microseconds=-1),
        timedelta(seconds=-1),
        timedelta(minutes=-5),
    ],
)
def test_negative_clock_skew_is_rejected(skew: timedelta) -> None:
    with pytest.raises(ValueError, match="clock_skew must not be negative"):
        _configuration(clock_skew=skew)


@pytest.mark.parametrize(
    "skew",
    [
        timedelta(minutes=5, microseconds=1),
        timedelta(minutes=5, seconds=1),
        timedelta(minutes=6),
        timedelta(hours=1),
        timedelta(days=1),
    ],
)
def test_clock_skew_above_five_minutes_is_rejected(skew: timedelta) -> None:
    with pytest.raises(ValueError, match="clock_skew must not exceed five minutes"):
        _configuration(clock_skew=skew)


@pytest.mark.parametrize("skew", [30, 30.0, "30", None, "PT30S", (30,)])
def test_a_non_timedelta_clock_skew_is_rejected(skew: Any) -> None:
    with pytest.raises(ValueError, match="clock_skew must be a timedelta"):
        _configuration(clock_skew=skew)


# --- Structural boundaries ------------------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        "client_secret",
        "secret",
        "enabled",
        "trusted",
        "is_active",
        "state",
        "nonce",
        "code_verifier",
        "code_challenge",
        "admission_id",
        "return_path",
        "session_id",
        "user_id",
        "workspace_id",
        "private_key",
        "signing_key",
        "jwks",
        "keys",
        "provider",
        "provider_name",
    ],
)
def test_model_carries_no_secret_trust_flag_or_session_data(name: str) -> None:
    assert not hasattr(_configuration(), name)


def test_the_jwks_reference_is_a_url_and_never_key_material() -> None:
    """LQ-156 configures where the key set lives, never the key set itself."""

    configuration = _configuration()

    assert isinstance(configuration.jwks_uri, str)
    assert configuration.jwks_uri.startswith("https://")
