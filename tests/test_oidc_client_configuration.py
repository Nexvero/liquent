from dataclasses import FrozenInstanceError, fields
from typing import Any

import pytest

from liquent_platform.identity import oidc_client_configuration as module
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)


ISSUER = "https://idp.example.test"
AUTHORIZATION_ENDPOINT = "https://idp.example.test/authorize"
CLIENT_ID = "liquent-control-plane"
REDIRECT_URI = "https://app.example.test/v1/oidc/callback"
SCOPES = ("openid",)


def _configuration(**overrides: Any) -> TrustedOidcClientConfiguration:
    arguments: dict[str, Any] = {
        "issuer": ISSUER,
        "authorization_endpoint": AUTHORIZATION_ENDPOINT,
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scopes": SCOPES,
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


def test_model_is_immutable() -> None:
    configuration = _configuration()

    with pytest.raises(FrozenInstanceError):
        configuration.client_id = "other"  # type: ignore[misc]


def test_model_is_hashable() -> None:
    assert hash(_configuration()) == hash(_configuration())


def test_model_has_exactly_the_five_agreed_fields_in_order() -> None:
    names = [field.name for field in fields(TrustedOidcClientConfiguration)]

    assert names == [
        "issuer",
        "authorization_endpoint",
        "client_id",
        "redirect_uri",
        "scopes",
    ]


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
    ],
)
def test_model_carries_no_secret_trust_flag_or_session_data(name: str) -> None:
    assert not hasattr(_configuration(), name)


def test_module_exposes_only_the_configuration_model() -> None:
    # No port, adapter, store, network call, or authorization URL builder is
    # added by this slice.
    public = {name for name in vars(module) if not name.startswith("_")}

    assert public == {"dataclass", "urlsplit", "TrustedOidcClientConfiguration"}
