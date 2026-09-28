from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from liquent_platform.application.internal_destination import (
    ValidatedInternalDestination,
)
from liquent_platform.identity.access import (
    CurrentWorkspaceContext,
    MembershipStatus,
    Permission,
    UserId,
    WorkspaceMembership,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import (
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipStoreUnavailable,
)
from liquent_platform.transport.http.app import create_app

USER = UserId("internal-user-2659")
WORKSPACE = WorkspaceId("internal-workspace-2659")
CONTEXT = CurrentWorkspaceContext(USER, WORKSPACE)


class Sessions:
    def get_session(self, session_id: SessionId) -> ResolvedBrowserSession | None:
        return ResolvedBrowserSession(
            principal=SessionPrincipal(USER), expected_csrf_token="private-csrf"
        )


class Contexts:
    def __init__(self, result: CurrentWorkspaceContext | None) -> None:
        self.result = result
        self.calls: list[UserId] = []

    def resolve_current_workspace(
        self, user_id: UserId
    ) -> CurrentWorkspaceContext | None:
        self.calls.append(user_id)
        return self.result


class Memberships:
    def __init__(self, result: WorkspaceMembership | None) -> None:
        self.result = result
        self.error: Exception | None = None
        self.calls: list[tuple[UserId, WorkspaceId]] = []

    def get_membership(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> WorkspaceMembership | None:
        self.calls.append((user_id, workspace_id))
        if self.error is not None:
            raise self.error
        return self.result


def _membership(
    *permissions: Permission,
    status: MembershipStatus = MembershipStatus.ACTIVE,
) -> WorkspaceMembership:
    return WorkspaceMembership(USER, WORKSPACE, status, frozenset(permissions))


def _client(contexts: Contexts, memberships: Memberships) -> TestClient:
    sessions = Sessions()
    dependencies: dict[str, Any] = {
        "oidc_callback_transactions": object(),
        "oidc_callback_verifier": object(),
        "oidc_callback_identities": object(),
        "oidc_callback_admissions": object(),
        "oidc_callback_sessions": object(),
        "oidc_callback_material": object(),
        "oidc_login_clock": lambda: datetime(2026, 9, 14, tzinfo=UTC),
        "oidc_session_lifetime": timedelta(hours=1),
        "oidc_callback_rejection": ValidatedInternalDestination("/login/rejected"),
        "oidc_callback_unavailable": ValidatedInternalDestination(
            "/login/unavailable"
        ),
        "logout_sessions": sessions,
        "logout_revocations": object(),
        "landing_workspace_contexts": contexts,
        "research_sessions": sessions,
        "research_memberships": memberships,
    }
    client = TestClient(create_app(**dependencies))
    client.cookies.set("liquent_session", "opaque-session")
    return client


@pytest.mark.parametrize(
    "permission", [Permission.RESEARCH_READ, Permission.RESEARCH_WRITE]
)
def test_indicator_requires_current_research_read_access(
    permission: Permission,
) -> None:
    contexts = Contexts(CONTEXT)
    memberships = Memberships(_membership(permission))

    response = _client(contexts, memberships).get("/")

    assert response.status_code == 200
    assert "Research read access is available." in response.text
    assert str(USER) not in response.text
    assert str(WORKSPACE) not in response.text
    assert contexts.calls == [USER]
    assert memberships.calls == [(USER, WORKSPACE)]


@pytest.mark.parametrize(
    "membership",
    [
        None,
        _membership(),
        _membership(Permission.RESEARCH_READ, status=MembershipStatus.INACTIVE),
    ],
)
def test_denial_preserves_workspace_landing_without_indicator(
    membership: WorkspaceMembership | None,
) -> None:
    response = _client(Contexts(CONTEXT), Memberships(membership)).get("/")

    assert response.status_code == 200
    assert "Your workspace context is available." in response.text
    assert "Research read access is available." not in response.text


def test_absent_context_stops_before_research_membership_lookup() -> None:
    contexts = Contexts(None)
    memberships = Memberships(_membership(Permission.RESEARCH_READ))

    response = _client(contexts, memberships).get("/")

    assert response.status_code == 200
    assert "No workspace context is available." in response.text
    assert "Research read access is available." not in response.text
    assert memberships.calls == []


def test_membership_unavailability_uses_existing_detail_free_outcome() -> None:
    memberships = Memberships(None)
    memberships.error = WorkspaceMembershipStoreUnavailable()

    response = _client(Contexts(CONTEXT), memberships).get(
        "/", follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login/unavailable"
    assert response.headers.get("set-cookie") is None
    assert response.content == b""


def test_rejected_input_stops_before_both_authority_lookups() -> None:
    contexts = Contexts(CONTEXT)
    memberships = Memberships(_membership(Permission.RESEARCH_READ))

    response = _client(contexts, memberships).get("/?workspace=caller-selected")

    assert response.status_code == 400
    assert contexts.calls == []
    assert memberships.calls == []
