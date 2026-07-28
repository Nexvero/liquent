from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import IdentityAdmissionRecord
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.research import WorkspaceId


NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)
USER = UserId("user-1")
WORKSPACE = WorkspaceId("workspace-1")
IDENTITY = ExternalIdentity("https://issuer.example", "subject-123")


def _active() -> IdentityAdmissionRecord:
    return IdentityAdmissionRecord(USER, WORKSPACE, NOW + timedelta(minutes=5))


def _consumed() -> IdentityAdmissionRecord:
    return IdentityAdmissionRecord(
        USER,
        WORKSPACE,
        NOW + timedelta(minutes=5),
        consumed_at=NOW,
        bound_identity=IDENTITY,
    )


def test_active_record_with_aware_expiry() -> None:
    record = _active()

    assert record.target_user_id == USER
    assert record.target_workspace_id == WORKSPACE
    assert record.expires_at == NOW + timedelta(minutes=5)
    assert record.consumed_at is None
    assert record.bound_identity is None


def test_consumed_record_keeps_bound_identity_and_consumed_at() -> None:
    record = _consumed()

    assert record.consumed_at == NOW
    assert record.bound_identity == IDENTITY


def test_naive_expires_at_is_rejected() -> None:
    with pytest.raises(ValueError, match="expires_at must be timezone-aware"):
        IdentityAdmissionRecord(USER, WORKSPACE, datetime(2026, 7, 28, 12))


def test_naive_consumed_at_is_rejected() -> None:
    with pytest.raises(ValueError, match="consumed_at must be timezone-aware"):
        IdentityAdmissionRecord(
            USER,
            WORKSPACE,
            NOW + timedelta(minutes=5),
            consumed_at=datetime(2026, 7, 28, 12),
            bound_identity=IDENTITY,
        )


def test_consumed_at_without_bound_identity_is_rejected() -> None:
    with pytest.raises(
        ValueError, match="consumed_at and bound_identity must be set together"
    ):
        IdentityAdmissionRecord(
            USER, WORKSPACE, NOW + timedelta(minutes=5), consumed_at=NOW
        )


def test_bound_identity_without_consumed_at_is_rejected() -> None:
    with pytest.raises(
        ValueError, match="consumed_at and bound_identity must be set together"
    ):
        IdentityAdmissionRecord(
            USER,
            WORKSPACE,
            NOW + timedelta(minutes=5),
            bound_identity=IDENTITY,
        )


def test_record_is_immutable() -> None:
    record = _active()

    with pytest.raises(FrozenInstanceError):
        record.consumed_at = NOW  # type: ignore[misc]


def test_record_is_hashable() -> None:
    assert hash(_consumed()) == hash(_consumed())
    assert hash(_active()) == hash(_active())


def test_model_has_exactly_the_five_agreed_fields() -> None:
    names = [field.name for field in fields(IdentityAdmissionRecord)]

    assert names == [
        "target_user_id",
        "target_workspace_id",
        "expires_at",
        "consumed_at",
        "bound_identity",
    ]


def test_model_has_no_claim_token_role_or_session_fields() -> None:
    names = {field.name for field in fields(IdentityAdmissionRecord)}
    forbidden = {
        "email",
        "claims",
        "token",
        "id_token",
        "access_token",
        "role",
        "roles",
        "permission",
        "permissions",
        "session",
        "session_id",
        "csrf",
    }

    assert names.isdisjoint(forbidden)


def test_target_workspace_grants_no_membership_or_permission() -> None:
    record = _active()

    # The record only bounds the intended context; it exposes no membership,
    # role, or permission and no method that would grant one.
    for attribute in ("membership", "role", "permission", "grant"):
        assert not hasattr(record, attribute)
