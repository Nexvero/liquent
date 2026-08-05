import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from liquent_platform.application.verify_oidc_callback import (
    VerifiedOidcCallback,
    verify_oidc_callback,
)
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
    OidcVerificationUnavailable,
)


NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)
STATE = OidcLoginState("opaque-state-1")
CODE = "authorization-code-1"

ISSUER = "https://idp.example.test"
NONCE = "expected-nonce-1"
VERIFIER_SECRET = "code-verifier-1"
REDIRECT_URI = "https://app.example.test/v1/session/oidc/callback"
ADMISSION = IdentityAdmissionId("admission-1")
RETURN_PATH = "/workspaces/w-1/research"

IDENTITY = ExternalIdentity(issuer=ISSUER, subject="subject-1")


def _transaction(**overrides: Any) -> PendingOidcLoginTransaction:
    arguments: dict[str, Any] = {
        "expected_issuer": ISSUER,
        "expected_nonce": NONCE,
        "code_verifier": VERIFIER_SECRET,
        "redirect_uri": REDIRECT_URI,
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=10),
        "admission_id": ADMISSION,
        "return_path": RETURN_PATH,
    }
    arguments.update(overrides)
    return PendingOidcLoginTransaction(**arguments)


class Recorder:
    """Shared call log so order and non-invocation can be asserted exactly."""

    def __init__(self) -> None:
        self.calls: list[str] = []


class StubClaimStore:
    def __init__(
        self,
        recorder: Recorder,
        transaction: PendingOidcLoginTransaction | None = None,
    ) -> None:
        self._recorder = recorder
        self._transaction = transaction
        self.claims: list[OidcLoginState] = []

    def claim_transaction(
        self, state: OidcLoginState
    ) -> PendingOidcLoginTransaction | None:
        self.claims.append(state)
        self._recorder.calls.append("claim")
        return self._transaction


class StubVerifier:
    def __init__(
        self,
        recorder: Recorder,
        identity: ExternalIdentity | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._recorder = recorder
        self._identity = identity
        self._error = error
        self.inputs: list[OidcAuthorizationCodeVerification] = []

    def verify_authorization_code(
        self, verification: OidcAuthorizationCodeVerification
    ) -> ExternalIdentity | None:
        self.inputs.append(verification)
        self._recorder.calls.append("verify")
        if self._error is not None:
            raise self._error
        return self._identity


# --- 1. Result object ------------------------------------------------------

def test_result_is_frozen_slotted_hashable_and_repr_free() -> None:
    result = VerifiedOidcCallback(IDENTITY, ADMISSION, RETURN_PATH)

    with pytest.raises(FrozenInstanceError):
        result.return_path = "/other"  # type: ignore[misc]
    assert VerifiedOidcCallback.__slots__ == (
        "identity",
        "admission_id",
        "return_path",
    )
    assert hash(result) == hash(VerifiedOidcCallback(IDENTITY, ADMISSION, RETURN_PATH))
    assert [field.name for field in fields(VerifiedOidcCallback)] == [
        "identity",
        "admission_id",
        "return_path",
    ]
    assert all(field.repr is False for field in fields(VerifiedOidcCallback))
    text = repr(result)
    assert text == "VerifiedOidcCallback()"
    for secret in (ISSUER, "subject-1", "admission-1", RETURN_PATH):
        assert secret not in text


def test_result_keeps_its_three_values_exactly() -> None:
    result = VerifiedOidcCallback(IDENTITY, ADMISSION, RETURN_PATH)

    assert result.identity is IDENTITY
    assert result.admission_id is ADMISSION
    assert result.return_path == RETURN_PATH


# --- 2. Claim returns None -------------------------------------------------

def test_an_unclaimable_state_ends_neutrally_without_the_verifier() -> None:
    """Unknown, expired, and already consumed are one neutral None."""

    recorder = Recorder()
    store = StubClaimStore(recorder, None)
    verifier = StubVerifier(recorder, IDENTITY)

    assert verify_oidc_callback(store, verifier, STATE, CODE) is None
    assert store.claims == [STATE]  # exactly once
    assert verifier.inputs == []
    assert recorder.calls == ["claim"]


# --- 3. Provider error form ------------------------------------------------

def test_a_provider_error_form_claims_once_and_skips_the_verifier() -> None:
    recorder = Recorder()
    store = StubClaimStore(recorder, _transaction())
    verifier = StubVerifier(recorder, IDENTITY)

    result = verify_oidc_callback(store, verifier, STATE, None)

    assert result is None  # the claimed transaction is not handed back
    assert store.claims == [STATE]
    assert verifier.inputs == []
    assert recorder.calls == ["claim"]


# --- 4. Malformed code from a direct caller --------------------------------

@pytest.mark.parametrize("code", ["", b"code", 1, 1.0, object()])
def test_an_empty_or_wrong_typed_code_still_claims_first_then_ends(
    code: Any,
) -> None:
    recorder = Recorder()
    store = StubClaimStore(recorder, _transaction())
    verifier = StubVerifier(recorder, IDENTITY)

    assert verify_oidc_callback(store, verifier, STATE, code) is None
    assert store.claims == [STATE]  # claimed fail-closed before the check
    assert verifier.inputs == []
    assert recorder.calls == ["claim"]


# --- 5. Success ------------------------------------------------------------

def test_success_claims_then_verifies_once_and_returns_the_record_values() -> None:
    recorder = Recorder()
    transaction = _transaction()
    store = StubClaimStore(recorder, transaction)
    verifier = StubVerifier(recorder, IDENTITY)

    result = verify_oidc_callback(store, verifier, STATE, CODE)

    assert recorder.calls == ["claim", "verify"]  # order is fixed
    assert store.claims == [STATE]
    assert len(verifier.inputs) == 1
    assert result is not None
    assert result.identity is IDENTITY
    assert result.admission_id is transaction.admission_id
    assert result.return_path == transaction.return_path


def test_the_verification_input_is_the_code_plus_the_claimed_record() -> None:
    recorder = Recorder()
    transaction = _transaction()
    verifier = StubVerifier(recorder, IDENTITY)

    verify_oidc_callback(
        StubClaimStore(recorder, transaction), verifier, STATE, CODE
    )

    sent = verifier.inputs[0]
    assert sent.authorization_code == CODE
    assert sent.expected_issuer == transaction.expected_issuer
    assert sent.expected_nonce == transaction.expected_nonce
    assert sent.code_verifier == transaction.code_verifier
    assert sent.redirect_uri == transaction.redirect_uri
    # Nothing else travels: no state, admission, or return path.
    assert [field.name for field in fields(OidcAuthorizationCodeVerification)] == [
        "authorization_code",
        "expected_issuer",
        "expected_nonce",
        "code_verifier",
        "redirect_uri",
    ]


def test_no_state_or_transaction_secret_reaches_the_result() -> None:
    recorder = Recorder()
    result = verify_oidc_callback(
        StubClaimStore(recorder, _transaction()),
        StubVerifier(recorder, IDENTITY),
        STATE,
        CODE,
    )

    assert result is not None
    names = {field.name for field in fields(VerifiedOidcCallback)}
    assert names.isdisjoint(
        {"state", "authorization_code", "expected_nonce", "code_verifier", "token"}
    )
    for name in ("state", "code_verifier", "expected_nonce"):
        assert not hasattr(result, name)


def test_an_absent_admission_and_return_path_are_carried_through_as_none() -> None:
    recorder = Recorder()
    transaction = _transaction(admission_id=None, return_path=None)

    result = verify_oidc_callback(
        StubClaimStore(recorder, transaction),
        StubVerifier(recorder, IDENTITY),
        STATE,
        CODE,
    )

    assert result is not None
    assert result.admission_id is None
    assert result.return_path is None


# --- 6. Verifier rejection -------------------------------------------------

def test_a_rejected_verification_ends_neutrally_without_retry() -> None:
    recorder = Recorder()
    store = StubClaimStore(recorder, _transaction())
    verifier = StubVerifier(recorder, None)

    assert verify_oidc_callback(store, verifier, STATE, CODE) is None
    assert recorder.calls == ["claim", "verify"]  # no retry, no second claim
    assert store.claims == [STATE]


# --- 7. Verifier unavailable -----------------------------------------------

def test_technical_unavailability_propagates_unchanged() -> None:
    recorder = Recorder()
    raised = OidcVerificationUnavailable()
    store = StubClaimStore(recorder, _transaction())
    verifier = StubVerifier(recorder, error=raised)

    with pytest.raises(OidcVerificationUnavailable) as caught:
        verify_oidc_callback(store, verifier, STATE, CODE)

    assert caught.value is raised  # the same object, not a re-wrapped one
    assert recorder.calls == ["claim", "verify"]
    assert store.claims == [STATE]


# --- 8. Signature boundary -------------------------------------------------

def test_signature_has_exactly_the_four_agreed_parameters() -> None:
    parameters = inspect.signature(verify_oidc_callback).parameters

    assert list(parameters) == [
        "transaction_store",
        "verifier",
        "state",
        "authorization_code",
    ]


@pytest.mark.parametrize(
    "name",
    [
        "now",
        "clock",
        "configuration",
        "request",
        "headers",
        "cookies",
        "cookie",
        "response",
        "query",
        "error",
        "error_description",
        "error_uri",
        "admission_id",
        "return_path",
    ],
)
def test_signature_has_no_clock_configuration_or_transport_parameter(
    name: str,
) -> None:
    assert name not in inspect.signature(verify_oidc_callback).parameters
