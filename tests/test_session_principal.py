from dataclasses import FrozenInstanceError, fields

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import ResolvedBrowserSession, SessionPrincipal


def test_session_principal_contains_only_verified_user_identity() -> None:
    principal = SessionPrincipal(user_id=UserId("user-1"))

    assert principal.user_id == "user-1"
    assert [field.name for field in fields(SessionPrincipal)] == ["user_id"]


def test_session_principal_is_immutable() -> None:
    principal = SessionPrincipal(user_id=UserId("user-1"))

    with pytest.raises(FrozenInstanceError):
        principal.user_id = UserId("user-2")  # type: ignore[misc]


def test_resolved_browser_session_binds_principal_and_expected_csrf() -> None:
    principal = SessionPrincipal(user_id=UserId("user-1"))
    session = ResolvedBrowserSession(principal, "private-csrf-proof")

    assert session.principal is principal
    assert session.expected_csrf_token == "private-csrf-proof"
    assert [field.name for field in fields(ResolvedBrowserSession)] == [
        "principal",
        "expected_csrf_token",
    ]


def test_resolved_browser_session_hides_csrf_from_representation() -> None:
    session = ResolvedBrowserSession(
        SessionPrincipal(UserId("user-1")),
        "private-csrf-proof",
    )

    assert "private-csrf-proof" not in repr(session)


def test_resolved_browser_session_requires_non_empty_csrf() -> None:
    with pytest.raises(ValueError, match="expected csrf token must not be empty"):
        ResolvedBrowserSession(SessionPrincipal(UserId("user-1")), "")


def test_resolved_browser_session_is_immutable() -> None:
    session = ResolvedBrowserSession(
        SessionPrincipal(UserId("user-1")),
        "private-csrf-proof",
    )

    with pytest.raises(FrozenInstanceError):
        session.expected_csrf_token = "replacement"  # type: ignore[misc]
