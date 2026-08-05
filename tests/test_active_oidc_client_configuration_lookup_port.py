import ast
import inspect
from datetime import timedelta

import pytest

import liquent_platform.identity.ports as ports_mod
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.ports import ActiveOidcClientConfigurationLookup


def _configuration(
    client_id: str = "liquent-control-plane",
) -> TrustedOidcClientConfiguration:
    return TrustedOidcClientConfiguration(
        issuer="https://idp.example.test",
        authorization_endpoint="https://idp.example.test/authorize",
        client_id=client_id,
        redirect_uri="https://app.example.test/v1/oidc/callback",
        scopes=("openid",),
        token_endpoint="https://idp.example.test/token",
        jwks_uri="https://idp.example.test/jwks",
        allowed_signing_algorithms=("RS256",),
        clock_skew=timedelta(seconds=30),
    )


class StubActiveConfigurationLookup:
    """Test-only stub for the read-only active configuration contract.

    The active configuration is mutable here only so a test can model an
    approval being granted or revoked between two lookups. It is not a
    production adapter.
    """

    def __init__(
        self, configuration: TrustedOidcClientConfiguration | None = None
    ) -> None:
        self.active = configuration
        self.calls = 0

    def get_active_configuration(self) -> TrustedOidcClientConfiguration | None:
        self.calls += 1
        return self.active


class ExplodingLookup:
    """Test-only stub whose read genuinely fails."""

    def get_active_configuration(self) -> TrustedOidcClientConfiguration | None:
        raise RuntimeError("configuration source unavailable")


# --- Contract --------------------------------------------------------------

def test_stub_satisfies_the_port_structurally() -> None:
    port: ActiveOidcClientConfigurationLookup = StubActiveConfigurationLookup()

    assert port.get_active_configuration() is None


def test_active_configuration_is_returned_unchanged() -> None:
    configuration = _configuration()
    port: ActiveOidcClientConfigurationLookup = StubActiveConfigurationLookup(
        configuration
    )

    result = port.get_active_configuration()

    # Exactly the stored object: no copy, no normalization, no added value.
    assert result is configuration
    assert result == _configuration()


def test_no_active_configuration_is_a_neutral_none() -> None:
    port: ActiveOidcClientConfigurationLookup = StubActiveConfigurationLookup(
        None
    )

    assert port.get_active_configuration() is None


def test_each_lookup_sees_the_current_state_and_freezes_no_trust() -> None:
    stub = StubActiveConfigurationLookup(_configuration())
    port: ActiveOidcClientConfigurationLookup = stub

    assert port.get_active_configuration() is not None
    stub.active = None  # approval revoked between two login starts
    assert port.get_active_configuration() is None
    stub.active = _configuration("rotated-client")
    assert port.get_active_configuration().client_id == "rotated-client"  # type: ignore[union-attr]
    assert stub.calls == 3


def test_a_failing_lookup_propagates_and_is_not_turned_into_none() -> None:
    port: ActiveOidcClientConfigurationLookup = ExplodingLookup()

    with pytest.raises(RuntimeError, match="configuration source unavailable"):
        port.get_active_configuration()


# --- No caller-driven provider selection -----------------------------------

def test_the_method_takes_only_self() -> None:
    parameters = inspect.signature(
        ActiveOidcClientConfigurationLookup.get_active_configuration
    ).parameters

    assert list(parameters) == ["self"]


@pytest.mark.parametrize(
    "name",
    [
        "issuer",
        "provider",
        "provider_name",
        "client_id",
        "tenant",
        "tenant_id",
        "workspace_id",
        "user_id",
        "host",
        "headers",
        "query",
        "cookie",
        "admission_id",
        "return_path",
    ],
)
def test_no_selector_parameter_exists(name: str) -> None:
    parameters = inspect.signature(
        ActiveOidcClientConfigurationLookup.get_active_configuration
    ).parameters

    assert name not in parameters


def test_return_annotation_allows_a_configuration_or_none() -> None:
    annotation = inspect.signature(
        ActiveOidcClientConfigurationLookup.get_active_configuration
    ).return_annotation

    # Compared against the evaluated union, not its spelling.
    assert annotation == TrustedOidcClientConfiguration | None


# --- Read-only, declaration only -------------------------------------------

def test_port_declares_only_the_read_method_without_a_body() -> None:
    # Structural, not textual: the docstring legitimately names activation and
    # rotation while ruling them out, so inspect the AST instead. Scoped to
    # this port only - it says nothing about the rest of ports.py.
    tree = ast.parse(inspect.getsource(ActiveOidcClientConfigurationLookup))
    methods = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ]

    # One read method and no mutation method is defined by this protocol.
    assert [node.name for node in methods] == ["get_active_configuration"]
    statements = [
        statement
        for statement in methods[0].body
        if not (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        )
    ]
    # A bare `...` declaration: no discovery, network, caching, or trust logic.
    assert len(statements) == 1
    assert isinstance(statements[0], ast.Expr)
    assert isinstance(statements[0].value, ast.Constant)
    assert statements[0].value.value is Ellipsis


def test_stubs_are_test_only_and_not_exported() -> None:
    import liquent_platform.identity as identity_pkg

    for name in ("StubActiveConfigurationLookup", "ExplodingLookup"):
        assert not hasattr(ports_mod, name)
        assert not hasattr(identity_pkg, name)
