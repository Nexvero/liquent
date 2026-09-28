import inspect
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta

import pytest

import liquent_platform.identity.oidc_login_transaction as mod
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.oidc_login_transaction import (
    PendingOidcLoginTransaction,
)


CREATED = datetime(2026, 7, 29, 12, tzinfo=UTC)
EXPIRES = CREATED + timedelta(minutes=10)
NAIVE = datetime(2026, 7, 29, 12)
ADMISSION = IdentityAdmissionId("admission-1")

REQUIRED = {
    "expected_issuer": "https://issuer.example",
    "expected_nonce": "nonce-y",
    "code_verifier": "verifier-z",
    "redirect_uri": "https://app.example/v1/session/oidc/callback",
    "created_at": CREATED,
    "expires_at": EXPIRES,
}


def _pending(**overrides: object) -> PendingOidcLoginTransaction:
    fields_ = {**REQUIRED, **overrides}
    return PendingOidcLoginTransaction(**fields_)  # type: ignore[arg-type]


# --- Valid record ----------------------------------------------------------

def test_valid_record_with_timezone_aware_times() -> None:
    transaction = _pending()

    assert transaction.expected_issuer == "https://issuer.example"
    assert transaction.expected_nonce == "nonce-y"
    assert transaction.code_verifier == "verifier-z"
    assert transaction.redirect_uri == (
        "https://app.example/v1/session/oidc/callback"
    )
    assert transaction.created_at == CREATED
    assert transaction.expires_at == EXPIRES
    assert transaction.admission_id is None
    assert transaction.return_path is None


def test_values_are_stored_verbatim_without_normalization() -> None:
    transaction = _pending(
        expected_issuer="HTTPS://Issuer.Example/",
        expected_nonce="  Nonce  ",
        redirect_uri="https://app.example/Callback/",
    )

    assert transaction.expected_issuer == "HTTPS://Issuer.Example/"
    assert transaction.expected_nonce == "  Nonce  "
    assert transaction.redirect_uri == "https://app.example/Callback/"


# --- Required strings ------------------------------------------------------

@pytest.mark.parametrize(
    "name",
    ["expected_issuer", "expected_nonce", "code_verifier", "redirect_uri"],
)
def test_required_strings_must_not_be_empty(name: str) -> None:
    with pytest.raises(ValueError, match=f"{name} must not be empty"):
        _pending(**{name: ""})


# --- Time invariants -------------------------------------------------------

def test_naive_created_at_is_rejected() -> None:
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        _pending(created_at=NAIVE)


def test_naive_expires_at_is_rejected() -> None:
    with pytest.raises(ValueError, match="expires_at must be timezone-aware"):
        _pending(expires_at=NAIVE)


def test_equal_created_at_and_expires_at_is_rejected() -> None:
    with pytest.raises(ValueError, match="expires_at must be after created_at"):
        _pending(expires_at=CREATED)


def test_expires_at_before_created_at_is_rejected() -> None:
    with pytest.raises(ValueError, match="expires_at must be after created_at"):
        _pending(expires_at=CREATED - timedelta(seconds=1))


# --- Optional fields -------------------------------------------------------

def test_optional_admission_id_is_preserved_exactly() -> None:
    transaction = _pending(admission_id=ADMISSION)

    assert transaction.admission_id == ADMISSION
    assert transaction.admission_id is ADMISSION


def test_optional_return_path_is_preserved_exactly() -> None:
    transaction = _pending(return_path="/workspaces/w-1/research")

    assert transaction.return_path == "/workspaces/w-1/research"


def test_empty_return_path_is_rejected_when_set() -> None:
    with pytest.raises(ValueError, match="return_path must not be empty"):
        _pending(return_path="")


# --- Object semantics ------------------------------------------------------

def test_record_is_immutable() -> None:
    transaction = _pending()

    with pytest.raises(FrozenInstanceError):
        transaction.code_verifier = "other"  # type: ignore[misc]


def test_record_is_hashable() -> None:
    assert hash(_pending()) == hash(_pending())
    assert hash(_pending(admission_id=ADMISSION, return_path="/x")) == hash(
        _pending(admission_id=ADMISSION, return_path="/x")
    )


def test_repr_hides_nonce_code_verifier_and_admission_id() -> None:
    # An IdentityAdmissionId can reference a single-use onboarding or binding
    # operation, so it is a sensitive capability handle.
    text = repr(
        _pending(
            expected_nonce="secret-nonce",
            code_verifier="secret-verifier",
            admission_id=IdentityAdmissionId("secret-admission"),
        )
    )

    assert "secret-nonce" not in text
    assert "secret-verifier" not in text
    assert "secret-admission" not in text


def test_repr_may_show_non_sensitive_metadata() -> None:
    text = repr(_pending(return_path="/workspaces/w-1"))

    assert "https://issuer.example" in text
    assert "https://app.example/v1/session/oidc/callback" in text
    assert "/workspaces/w-1" in text


# --- Structural boundaries -------------------------------------------------

def test_model_has_exactly_the_eight_agreed_fields() -> None:
    names = [f.name for f in fields(PendingOidcLoginTransaction)]

    assert names == [
        "expected_issuer",
        "expected_nonce",
        "code_verifier",
        "redirect_uri",
        "created_at",
        "expires_at",
        "expected_trust_revision",
        "admission_id",
        "return_path",
    ]


def test_model_has_no_state_or_code_challenge_field() -> None:
    names = {f.name for f in fields(PendingOidcLoginTransaction)}

    # state is the later opaque store key; code_challenge is only needed for the
    # authorization request. Neither is stored redundantly in the record.
    assert names.isdisjoint({"state", "code_challenge", "code_challenge_method"})


def test_model_has_no_token_claim_user_workspace_role_or_session_fields() -> None:
    names = {f.name for f in fields(PendingOidcLoginTransaction)}
    forbidden = {
        "token",
        "id_token",
        "access_token",
        "refresh_token",
        "code",
        "authorization_code",
        "claims",
        "email",
        "subject",
        "user_id",
        "workspace_id",
        "membership",
        "role",
        "roles",
        "permission",
        "permissions",
        "session",
        "session_id",
        "csrf",
    }

    assert names.isdisjoint(forbidden)


def test_record_carries_no_trust_store_or_consumption_logic() -> None:
    transaction = _pending()
    source = inspect.getsource(mod)

    for attribute in ("consume", "claim", "is_valid", "is_expired", "trust"):
        assert not hasattr(transaction, attribute)
    assert "Protocol" not in source
    assert "Store" not in source
    assert "fastapi" not in source
    assert "router" not in source.lower()
