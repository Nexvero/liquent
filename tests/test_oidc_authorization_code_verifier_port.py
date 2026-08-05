import ast
import inspect

import pytest

import liquent_platform.identity.ports as ports_mod
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
    OidcVerificationUnavailable,
)
from liquent_platform.identity.ports import OidcAuthorizationCodeVerifier


ISSUER = "https://idp.example.test"
SUBJECT = "subject-1"


def _verification() -> OidcAuthorizationCodeVerification:
    return OidcAuthorizationCodeVerification(
        authorization_code="authorization-code-1",
        expected_issuer=ISSUER,
        expected_nonce="expected-nonce-1",
        code_verifier="code-verifier-1",
        redirect_uri="https://app.example.test/v1/session/oidc/callback",
    )


# --- Test-only stub --------------------------------------------------------

class StubVerifier:
    """Test-only stub modelling the three outcomes of the verification port.

    It performs no redemption, no signature check, and no network call. It only
    models the contract: one verified identity, a neutral None for every
    business rejection, or OidcVerificationUnavailable for technical
    unavailability. It is not a production adapter.
    """

    def __init__(
        self,
        identity: ExternalIdentity | None = None,
        *,
        unavailable: bool = False,
        rejection_cause: str | None = None,
    ) -> None:
        self._identity = identity
        self._unavailable = unavailable
        # Modelled internally so a test can prove that a distinct internal
        # cause never becomes distinguishable from the outside.
        self._rejection_cause = rejection_cause
        self.calls: list[OidcAuthorizationCodeVerification] = []

    def verify_authorization_code(
        self,
        verification: OidcAuthorizationCodeVerification,
    ) -> ExternalIdentity | None:
        self.calls.append(verification)
        if self._unavailable:
            # Technical unavailability, never a business rejection.
            raise OidcVerificationUnavailable
        return self._identity


def _verified() -> ExternalIdentity:
    return ExternalIdentity(issuer=ISSUER, subject=SUBJECT)


# --- Success ---------------------------------------------------------------

def test_success_returns_exactly_one_external_identity() -> None:
    identity = _verified()
    port: OidcAuthorizationCodeVerifier = StubVerifier(identity)

    result = port.verify_authorization_code(_verification())

    assert result is identity
    assert isinstance(result, ExternalIdentity)


def test_the_verified_result_carries_only_issuer_and_subject() -> None:
    port: OidcAuthorizationCodeVerifier = StubVerifier(_verified())

    result = port.verify_authorization_code(_verification())

    assert result is not None
    assert result.issuer == ISSUER
    assert result.subject == SUBJECT
    for forbidden in ("id_token", "access_token", "claims", "admission_id", "session"):
        assert not hasattr(result, forbidden)


def test_the_input_reaches_the_port_unchanged() -> None:
    verification = _verification()
    stub = StubVerifier(_verified())

    stub.verify_authorization_code(verification)

    assert stub.calls == [verification]
    assert stub.calls[0] is verification


# --- Business rejection ----------------------------------------------------

def test_a_business_rejection_is_a_neutral_none() -> None:
    port: OidcAuthorizationCodeVerifier = StubVerifier(None)

    assert port.verify_authorization_code(_verification()) is None


REJECTION_CAUSES = [
    "no active configuration",
    "expected issuer no longer active",
    "authorization code refused or invalid",
    "id token missing or invalid",
    "signature, algorithm, or key failure",
    "issuer or audience mismatch",
    "azp, exp, nbf, or iat failure",
    "nonce mismatch",
    "missing or empty subject",
]


@pytest.mark.parametrize("cause", REJECTION_CAUSES)
def test_every_business_rejection_cause_looks_identical(cause: str) -> None:
    """The stub holds a distinct internal cause; the outside sees only None."""

    port: OidcAuthorizationCodeVerifier = StubVerifier(None, rejection_cause=cause)

    result = port.verify_authorization_code(_verification())

    assert result is None
    # The cause stays internal: it is not returned and not rendered anywhere.
    assert cause not in repr(result)


def test_all_rejection_causes_are_indistinguishable_from_one_another() -> None:
    results = [
        StubVerifier(None, rejection_cause=cause).verify_authorization_code(
            _verification()
        )
        for cause in REJECTION_CAUSES
    ]

    # Nine different internal causes, one identical external answer.
    assert results == [None] * len(REJECTION_CAUSES)
    assert len(set(map(repr, results))) == 1


def test_a_rejection_carries_no_cause_object() -> None:
    result = StubVerifier(None).verify_authorization_code(_verification())

    assert result is None
    assert not isinstance(result, ExternalIdentity)


# --- Technical unavailability ----------------------------------------------

def test_technical_unavailability_raises_exactly_the_neutral_error() -> None:
    port: OidcAuthorizationCodeVerifier = StubVerifier(unavailable=True)

    with pytest.raises(OidcVerificationUnavailable) as raised:
        port.verify_authorization_code(_verification())

    assert str(raised.value) == "oidc_verification_unavailable"


def test_unavailability_is_raised_and_never_returned_as_none() -> None:
    port: OidcAuthorizationCodeVerifier = StubVerifier(unavailable=True)

    with pytest.raises(OidcVerificationUnavailable):
        port.verify_authorization_code(_verification())


def test_the_neutral_error_never_carries_the_input_values() -> None:
    verification = _verification()
    port: OidcAuthorizationCodeVerifier = StubVerifier(unavailable=True)

    with pytest.raises(OidcVerificationUnavailable) as raised:
        port.verify_authorization_code(verification)

    rendered = f"{raised.value}{raised.value.args}"
    for secret in (
        "authorization-code-1",
        "expected-nonce-1",
        "code-verifier-1",
        ISSUER,
        "https://app.example.test/v1/session/oidc/callback",
    ):
        assert secret not in rendered


def test_a_business_rejection_does_not_raise() -> None:
    port: OidcAuthorizationCodeVerifier = StubVerifier(None)

    # None and the neutral error are two different channels, never merged.
    assert port.verify_authorization_code(_verification()) is None


# --- Structural boundaries -------------------------------------------------

def test_port_is_structurally_compatible() -> None:
    identity = _verified()
    port: OidcAuthorizationCodeVerifier = StubVerifier(identity)

    assert port.verify_authorization_code(_verification()) is identity


def test_signature_has_only_self_and_verification() -> None:
    parameters = inspect.signature(
        OidcAuthorizationCodeVerifier.verify_authorization_code
    ).parameters

    assert list(parameters) == ["self", "verification"]


@pytest.mark.parametrize(
    "name",
    [
        "authorization_code",
        "code",
        "state",
        "configuration",
        "client_configuration",
        "now",
        "clock",
        "issuer",
        "expected_issuer",
        "provider",
        "tenant",
        "client_id",
        "host",
        "headers",
        "cookies",
        "request",
        "admission_id",
        "return_path",
    ],
)
def test_signature_has_no_separate_code_state_configuration_or_request_parameter(
    name: str,
) -> None:
    parameters = inspect.signature(
        OidcAuthorizationCodeVerifier.verify_authorization_code
    ).parameters

    assert name not in parameters


def test_the_single_parameter_is_annotated_as_the_verification_input() -> None:
    annotation = inspect.signature(
        OidcAuthorizationCodeVerifier.verify_authorization_code
    ).parameters["verification"].annotation

    assert annotation is OidcAuthorizationCodeVerification


def test_return_annotation_is_only_external_identity_or_none() -> None:
    annotation = inspect.signature(
        OidcAuthorizationCodeVerifier.verify_authorization_code
    ).return_annotation

    assert annotation == ExternalIdentity | None


def test_port_declares_only_verify_authorization_code_without_a_body() -> None:
    # Structural and scoped to this port only: it says nothing about the rest of
    # ports.py, its imports, other protocols, or any later addition.
    tree = ast.parse(inspect.getsource(OidcAuthorizationCodeVerifier))
    methods = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

    assert [node.name for node in methods] == ["verify_authorization_code"]
    statements = [
        statement
        for statement in methods[0].body
        if not (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        )
    ]
    # A bare `...` declaration: no adapter, redemption, or token logic here.
    assert len(statements) == 1
    assert isinstance(statements[0], ast.Expr)
    assert isinstance(statements[0].value, ast.Constant)
    assert statements[0].value.value is Ellipsis


def test_stub_is_test_only_and_not_exported() -> None:
    import liquent_platform.identity as identity_pkg

    assert not hasattr(ports_mod, "StubVerifier")
    assert not hasattr(identity_pkg, "StubVerifier")
