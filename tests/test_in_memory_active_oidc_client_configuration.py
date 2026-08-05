import inspect
from dataclasses import FrozenInstanceError
from datetime import timedelta

import pytest

from liquent_platform.identity.in_memory import (
    InMemoryActiveOidcClientConfiguration,
)
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.ports import ActiveOidcClientConfigurationLookup


ISSUER = "https://idp.example.test"
AUTHORIZATION_ENDPOINT = "https://idp.example.test/authorize"
CLIENT_ID = "liquent-control-plane"
REDIRECT_URI = "https://app.example.test/v1/oidc/callback"
SCOPES = ("openid", "email")


def _configuration() -> TrustedOidcClientConfiguration:
    return TrustedOidcClientConfiguration(
        issuer=ISSUER,
        authorization_endpoint=AUTHORIZATION_ENDPOINT,
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scopes=SCOPES,
        token_endpoint="https://idp.example.test/token",
        jwks_uri="https://idp.example.test/jwks",
        allowed_signing_algorithms=("RS256",),
        clock_skew=timedelta(seconds=30),
    )


# --- With a configuration ---------------------------------------------------

def test_adapter_is_structurally_compatible_with_the_port() -> None:
    port: ActiveOidcClientConfigurationLookup = (
        InMemoryActiveOidcClientConfiguration(_configuration())
    )

    assert port.get_active_configuration() is not None


def test_lookup_returns_exactly_the_given_object() -> None:
    configuration = _configuration()
    adapter = InMemoryActiveOidcClientConfiguration(configuration)

    assert adapter.get_active_configuration() is configuration


def test_repeated_lookups_return_the_same_object() -> None:
    adapter = InMemoryActiveOidcClientConfiguration(_configuration())

    first = adapter.get_active_configuration()
    second = adapter.get_active_configuration()

    assert first is second


def test_the_stored_values_are_left_unchanged() -> None:
    adapter = InMemoryActiveOidcClientConfiguration(_configuration())

    result = adapter.get_active_configuration()

    # Nothing copied, normalized, extended, or rebuilt.
    assert result == _configuration()
    assert result.issuer == ISSUER  # type: ignore[union-attr]
    assert result.authorization_endpoint == AUTHORIZATION_ENDPOINT  # type: ignore[union-attr]
    assert result.client_id == CLIENT_ID  # type: ignore[union-attr]
    assert result.redirect_uri == REDIRECT_URI  # type: ignore[union-attr]
    assert result.scopes == SCOPES  # type: ignore[union-attr]


# --- Without a configuration ------------------------------------------------

def test_construction_without_an_argument_yields_none() -> None:
    assert InMemoryActiveOidcClientConfiguration().get_active_configuration() is None


def test_an_explicit_none_yields_none() -> None:
    adapter = InMemoryActiveOidcClientConfiguration(None)

    assert adapter.get_active_configuration() is None


def test_repeated_empty_lookups_stay_none() -> None:
    adapter = InMemoryActiveOidcClientConfiguration()

    assert adapter.get_active_configuration() is None
    assert adapter.get_active_configuration() is None


# --- Immutability -----------------------------------------------------------

def test_adapter_is_immutable() -> None:
    adapter = InMemoryActiveOidcClientConfiguration(_configuration())

    with pytest.raises(FrozenInstanceError):
        adapter.configuration = None  # type: ignore[misc]


def test_the_stored_configuration_cannot_be_replaced() -> None:
    configuration = _configuration()
    adapter = InMemoryActiveOidcClientConfiguration(configuration)

    with pytest.raises(FrozenInstanceError):
        adapter.configuration = TrustedOidcClientConfiguration(  # type: ignore[misc]
            issuer="https://other.example.test",
            authorization_endpoint="https://other.example.test/authorize",
            client_id="other",
            redirect_uri="https://other.example.test/cb",
            scopes=("openid",),
            token_endpoint="https://other.example.test/token",
            jwks_uri="https://other.example.test/jwks",
            allowed_signing_algorithms=("RS256",),
            clock_skew=timedelta(seconds=30),
        )
    assert adapter.get_active_configuration() is configuration


@pytest.mark.parametrize(
    "name",
    [
        "set_configuration",
        "replace_configuration",
        "activate",
        "deactivate",
        "delete",
        "clear",
        "reload",
        "refresh",
        "discover",
    ],
)
def test_no_public_mutation_or_management_api(name: str) -> None:
    assert not hasattr(InMemoryActiveOidcClientConfiguration(), name)


# --- repr boundary ----------------------------------------------------------

def test_repr_shows_the_class_name_but_not_the_configuration() -> None:
    text = repr(InMemoryActiveOidcClientConfiguration(_configuration()))

    assert "InMemoryActiveOidcClientConfiguration" in text
    for value in (ISSUER, AUTHORIZATION_ENDPOINT, CLIENT_ID, REDIRECT_URI):
        assert value not in text
    for scope in SCOPES:
        assert scope not in text


# --- Signatures: no selector, no clock, no dependency -----------------------

def test_the_lookup_takes_only_self() -> None:
    parameters = inspect.signature(
        InMemoryActiveOidcClientConfiguration.get_active_configuration
    ).parameters

    assert list(parameters) == ["self"]


def test_the_return_annotation_matches_the_port() -> None:
    adapter_annotation = inspect.signature(
        InMemoryActiveOidcClientConfiguration.get_active_configuration
    ).return_annotation
    port_annotation = inspect.signature(
        ActiveOidcClientConfigurationLookup.get_active_configuration
    ).return_annotation

    assert adapter_annotation == port_annotation
    assert adapter_annotation == TrustedOidcClientConfiguration | None


@pytest.mark.parametrize(
    "name",
    [
        "issuer",
        "provider",
        "client_id",
        "tenant",
        "workspace_id",
        "user_id",
        "host",
        "headers",
        "cookie",
        "admission_id",
        "return_path",
    ],
)
def test_the_lookup_has_no_selector_parameter(name: str) -> None:
    parameters = inspect.signature(
        InMemoryActiveOidcClientConfiguration.get_active_configuration
    ).parameters

    assert name not in parameters


def test_construction_takes_only_the_configuration() -> None:
    # No now/clock, generator, network client, or discovery dependency is
    # injected, unlike InMemoryOidcLoginTransactions which does take a clock.
    parameters = inspect.signature(
        InMemoryActiveOidcClientConfiguration.__init__
    ).parameters

    assert list(parameters) == ["self", "configuration"]
