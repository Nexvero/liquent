import inspect
from dataclasses import FrozenInstanceError, fields
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import pytest

from liquent_platform.application.build_oidc_authorization_request import (
    OidcAuthorizationRequest,
    build_oidc_authorization_request,
)
from liquent_platform.application.start_oidc_login import StartedOidcLogin
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)


ENDPOINT = "https://idp.example.test/oauth2/authorize"
CLIENT_ID = "liquent-control-plane"
REDIRECT_URI = "https://app.example.test/v1/oidc/callback"
STATE = "generated-state"
NONCE = "generated-nonce"
CODE_CHALLENGE = "generated-challenge"

EXPECTED_PARAMETERS = [
    "response_type",
    "response_mode",
    "client_id",
    "redirect_uri",
    "scope",
    "state",
    "nonce",
    "code_challenge",
    "code_challenge_method",
]


def _configuration(**overrides: Any) -> TrustedOidcClientConfiguration:
    arguments: dict[str, Any] = {
        "issuer": "https://idp.example.test",
        "authorization_endpoint": ENDPOINT,
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scopes": ("openid",),
    }
    arguments.update(overrides)
    return TrustedOidcClientConfiguration(**arguments)


def _started(**overrides: Any) -> StartedOidcLogin:
    arguments: dict[str, Any] = {
        "state": STATE,
        "nonce": NONCE,
        "code_challenge": CODE_CHALLENGE,
    }
    arguments.update(overrides)
    return StartedOidcLogin(**arguments)


def _build(**overrides: Any) -> OidcAuthorizationRequest:
    configuration_keys = {
        "issuer",
        "authorization_endpoint",
        "client_id",
        "redirect_uri",
        "scopes",
    }
    configuration = _configuration(
        **{k: v for k, v in overrides.items() if k in configuration_keys}
    )
    started = _started(
        **{k: v for k, v in overrides.items() if k not in configuration_keys}
    )
    return build_oidc_authorization_request(configuration, started)


def _query(request: OidcAuthorizationRequest) -> list[tuple[str, str]]:
    """Decode the query structurally rather than by substring matching."""

    return parse_qsl(urlsplit(request.url).query, keep_blank_values=True)


def _parameters(request: OidcAuthorizationRequest) -> dict[str, str]:
    return dict(_query(request))


# --- Success and structure -------------------------------------------------

def test_a_valid_request_is_built() -> None:
    assert _build().url.startswith(f"{ENDPOINT}?")


def test_request_is_immutable() -> None:
    request = _build()

    with pytest.raises(FrozenInstanceError):
        request.url = "https://elsewhere.example.test"  # type: ignore[misc]


def test_request_is_hashable() -> None:
    assert hash(_build()) == hash(_build())


def test_request_has_exactly_the_url_field() -> None:
    assert [field.name for field in fields(OidcAuthorizationRequest)] == ["url"]


def test_repr_hides_the_url_but_keeps_the_class_name() -> None:
    text = repr(_build())

    assert "OidcAuthorizationRequest" in text
    for secret in (ENDPOINT, STATE, NONCE, CODE_CHALLENGE, CLIENT_ID, REDIRECT_URI):
        assert secret not in text


def test_url_stays_available_through_the_attribute() -> None:
    request = _build()

    assert request.url == f"{ENDPOINT}?{urlsplit(request.url).query}"


# --- Endpoint --------------------------------------------------------------

def test_endpoint_is_kept_exactly_in_front_of_the_query() -> None:
    url = _build().url

    assert url.split("?", 1)[0] == ENDPOINT


def test_endpoint_path_and_explicit_port_are_preserved() -> None:
    endpoint = "https://idp.example.test:8443/Tenant/OAuth2/Authorize"

    parsed = urlsplit(_build(authorization_endpoint=endpoint).url)

    assert parsed.scheme == "https"
    assert parsed.netloc == "idp.example.test:8443"
    assert parsed.path == "/Tenant/OAuth2/Authorize"


def test_no_fragment_is_produced() -> None:
    assert urlsplit(_build(nonce="nonce#with-hash").url).fragment == ""


def test_no_other_host_or_endpoint_is_derived() -> None:
    # The redirect uri lives on a different host and must not become the target.
    parsed = urlsplit(_build(redirect_uri="https://other.example.test/cb").url)

    assert parsed.netloc == "idp.example.test"
    assert parsed.path == "/oauth2/authorize"


# --- Exact parameter surface ----------------------------------------------

def test_exactly_the_nine_agreed_parameters_in_a_fixed_order() -> None:
    assert [name for name, _value in _query(_build())] == EXPECTED_PARAMETERS


def test_every_parameter_appears_exactly_once() -> None:
    names = [name for name, _value in _query(_build())]

    assert len(names) == len(set(names)) == 9


def test_the_order_is_deterministic_across_builds() -> None:
    assert _build().url == _build().url


@pytest.mark.parametrize(
    ("parameter", "expected"),
    [
        ("response_type", "code"),
        ("response_mode", "query"),
        ("code_challenge_method", "S256"),
    ],
)
def test_constant_parameters_have_their_fixed_values(
    parameter: str, expected: str
) -> None:
    assert _parameters(_build())[parameter] == expected


def test_configuration_values_are_taken_verbatim() -> None:
    parameters = _parameters(_build())

    assert parameters["client_id"] == CLIENT_ID
    assert parameters["redirect_uri"] == REDIRECT_URI


def test_scope_joins_the_configured_tuple_order_with_single_spaces() -> None:
    scopes = ("openid", "email", "profile")

    assert _parameters(_build(scopes=scopes))["scope"] == "openid email profile"


def test_started_login_values_are_taken_verbatim() -> None:
    parameters = _parameters(_build())

    assert parameters["state"] == STATE
    assert parameters["nonce"] == NONCE
    assert parameters["code_challenge"] == CODE_CHALLENGE


# --- Safe encoding ---------------------------------------------------------

def test_an_ampersand_in_the_client_id_cannot_add_a_parameter() -> None:
    request = _build(client_id="abc&injected=1")

    assert [name for name, _value in _query(request)] == EXPECTED_PARAMETERS
    assert _parameters(request)["client_id"] == "abc&injected=1"


def test_an_equals_sign_stays_part_of_the_state_value() -> None:
    assert _parameters(_build(state="a=b=c"))["state"] == "a=b=c"


def test_a_hash_in_the_nonce_produces_no_fragment() -> None:
    request = _build(nonce="n#frag")

    assert urlsplit(request.url).fragment == ""
    assert _parameters(request)["nonce"] == "n#frag"


def test_a_redirect_uri_with_a_fixed_query_stays_one_parameter_value() -> None:
    redirect_uri = "https://app.example.test/v1/oidc/callback?tenant=Acme&x=1"

    request = _build(redirect_uri=redirect_uri)

    assert [name for name, _value in _query(request)] == EXPECTED_PARAMETERS
    assert _parameters(request)["redirect_uri"] == redirect_uri


def test_reserved_characters_in_scopes_survive_decoding() -> None:
    scopes = ("openid", "https://api.example.test/data.read")

    parameters = _parameters(_build(scopes=scopes))

    assert parameters["scope"] == "openid https://api.example.test/data.read"


def test_unicode_values_round_trip_exactly() -> None:
    parameters = _parameters(_build(state="zustand-äöü-✓"))

    assert parameters["state"] == "zustand-äöü-✓"


def test_no_input_can_override_a_mandatory_parameter() -> None:
    request = _build(
        client_id="x&response_type=token",
        state="y&code_challenge_method=plain",
    )
    parameters = _parameters(request)

    assert [name for name, _value in _query(request)] == EXPECTED_PARAMETERS
    assert parameters["response_type"] == "code"
    assert parameters["code_challenge_method"] == "S256"


# --- Secret and data boundary ---------------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        "code_verifier",
        "admission_id",
        "return_path",
        "access_token",
        "id_token",
        "claims",
        "user_id",
        "workspace_id",
        "role",
        "session_id",
        "prompt",
        "login_hint",
        "domain_hint",
        "hd",
        "max_age",
        "acr_values",
        "ui_locales",
        "offline_access",
    ],
)
def test_no_forbidden_parameter_is_emitted(name: str) -> None:
    assert name not in _parameters(_build())


def test_offline_access_stays_inside_the_scope_value_when_configured() -> None:
    request = _build(scopes=("openid", "offline_access"))
    parameters = _parameters(request)

    assert [name for name, _value in _query(request)] == EXPECTED_PARAMETERS
    assert parameters["scope"] == "openid offline_access"
    assert "offline_access" not in {name for name, _value in _query(request)}


def test_request_object_carries_no_parameter_fields() -> None:
    request = _build()

    for name in ("state", "nonce", "code_verifier", "client_id", "admission_id"):
        assert not hasattr(request, name)


# --- Architectural boundary ------------------------------------------------

def test_builder_takes_only_the_two_validated_inputs() -> None:
    # No store, generator, clock, trust registry, or transport is injected.
    parameters = inspect.signature(build_oidc_authorization_request).parameters

    assert list(parameters) == ["configuration", "started"]


def test_building_twice_is_pure_and_generates_nothing() -> None:
    configuration = _configuration()
    started = _started()

    first = build_oidc_authorization_request(configuration, started)
    second = build_oidc_authorization_request(configuration, started)

    assert first == second


def test_the_inputs_are_left_unchanged() -> None:
    configuration = _configuration()
    started = _started()

    build_oidc_authorization_request(configuration, started)

    assert configuration == _configuration()
    assert started == _started()
