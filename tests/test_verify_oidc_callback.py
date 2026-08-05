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
ADMISSION = IdentityAdmissionId("admission-1")
RETURN_PATH = "/workspaces/w-1/research"
IDENTITY = ExternalIdentity(issuer=ISSUER, subject="subject-1")


def _transaction(**overrides: Any) -> PendingOidcLoginTransaction:
    arguments: dict[str, Any] = {
        "expected_issuer": ISSUER,
        "expected_nonce": "expected-nonce-1",
        "code_verifier": "code-verifier-1",
        "redirect_uri": "https://app.example.test/v1/session/oidc/callback",
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


def test_result_is_frozen_slotted_hashable_repr_free_and_exact() -> None:
    result = VerifiedOidcCallback(IDENTITY, ADMISSION, RETURN_PATH)

    with pytest.raises(FrozenInstanceError):
        result.return_path = "/other"  # type: ignore[misc]
    names = ["identity", "admission_id", "return_path"]
    assert VerifiedOidcCallback.__slots__ == tuple(names)
    assert [field.name for field in fields(VerifiedOidcCallback)] == names
    assert all(field.repr is False for field in fields(VerifiedOidcCallback))
    assert repr(result) == "VerifiedOidcCallback()"
    assert hash(result) == hash(VerifiedOidcCallback(IDENTITY, ADMISSION, RETURN_PATH))
    assert result.identity is IDENTITY
    assert result.admission_id is ADMISSION
    assert result.return_path == RETURN_PATH


def test_an_unclaimable_state_ends_neutrally_without_the_verifier() -> None:
    """Unknown, expired, and already consumed are one neutral None."""

    recorder = Recorder()
    store = StubClaimStore(recorder, None)
    verifier = StubVerifier(recorder, IDENTITY)

    assert verify_oidc_callback(store, verifier, STATE, CODE) is None
    assert store.claims == [STATE]
    assert recorder.calls == ["claim"]


@pytest.mark.parametrize("code", [None, "", 1])
def test_an_unusable_code_still_claims_first_then_ends(code: Any) -> None:
    """A provider-error form, an empty code, and a wrong type all fail closed."""

    recorder = Recorder()
    store = StubClaimStore(recorder, _transaction())
    verifier = StubVerifier(recorder, IDENTITY)

    assert verify_oidc_callback(store, verifier, STATE, code) is None
    assert store.claims == [STATE]
    assert recorder.calls == ["claim"]  # claimed, verifier untouched


def test_success_claims_then_verifies_once_with_the_claimed_record() -> None:
    recorder = Recorder()
    transaction = _transaction()
    store = StubClaimStore(recorder, transaction)
    verifier = StubVerifier(recorder, IDENTITY)

    result = verify_oidc_callback(store, verifier, STATE, CODE)

    assert recorder.calls == ["claim", "verify"]  # order, each exactly once
    sent = verifier.inputs[0]
    assert sent.authorization_code == CODE
    assert sent.expected_issuer == transaction.expected_issuer
    assert sent.expected_nonce == transaction.expected_nonce
    assert sent.code_verifier == transaction.code_verifier
    assert sent.redirect_uri == transaction.redirect_uri
    assert result is not None
    assert result.identity is IDENTITY
    assert result.admission_id is transaction.admission_id
    assert result.return_path == transaction.return_path


def test_an_absent_admission_and_return_path_pass_through_as_none() -> None:
    recorder = Recorder()

    result = verify_oidc_callback(
        StubClaimStore(recorder, _transaction(admission_id=None, return_path=None)),
        StubVerifier(recorder, IDENTITY),
        STATE,
        CODE,
    )

    assert result is not None
    assert result.admission_id is None
    assert result.return_path is None


def test_a_rejected_verification_ends_neutrally_without_retry() -> None:
    recorder = Recorder()
    store = StubClaimStore(recorder, _transaction())

    assert verify_oidc_callback(store, StubVerifier(recorder, None), STATE, CODE) is None
    assert recorder.calls == ["claim", "verify"]
    assert store.claims == [STATE]


def test_technical_unavailability_propagates_unchanged() -> None:
    recorder = Recorder()
    raised = OidcVerificationUnavailable()
    store = StubClaimStore(recorder, _transaction())

    with pytest.raises(OidcVerificationUnavailable) as caught:
        verify_oidc_callback(store, StubVerifier(recorder, error=raised), STATE, CODE)

    assert caught.value is raised  # the same object, not re-wrapped
    assert recorder.calls == ["claim", "verify"]
    assert store.claims == [STATE]


def test_signature_has_exactly_the_four_agreed_parameters() -> None:
    assert list(inspect.signature(verify_oidc_callback).parameters) == [
        "transaction_store",
        "verifier",
        "state",
        "authorization_code",
    ]
