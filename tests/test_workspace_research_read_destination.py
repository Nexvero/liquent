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

USER = UserId("internal-user-2660")
WORKSPACE = WorkspaceId("internal-workspace-2660")
CONTEXT = CurrentWorkspaceContext(USER, WORKSPACE)


class Sessions:
    def __init__(self) -> None:
        self.calls: list[SessionId] = []

    def get_session(self, session_id: SessionId) -> ResolvedBrowserSession | None:
        self.calls.append(session_id)
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


def _client(
    contexts: Contexts,
    memberships: Memberships,
) -> tuple[TestClient, Sessions]:
    sessions = Sessions()
    dependencies: dict[str, Any] = {
        "oidc_callback_transactions": object(),
        "oidc_callback_verifier": object(),
        "oidc_callback_identities": object(),
        "oidc_callback_admissions": object(),
        "oidc_callback_sessions": object(),
        "oidc_callback_material": object(),
        "oidc_login_clock": lambda: datetime(2026, 9, 15, tzinfo=UTC),
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
    return client, sessions


@pytest.mark.parametrize(
    "permission", [Permission.RESEARCH_READ, Permission.RESEARCH_WRITE]
)
def test_current_authority_opens_detail_free_read_destination(
    permission: Permission,
) -> None:
    contexts = Contexts(CONTEXT)
    memberships = Memberships(_membership(permission))
    client, _ = _client(contexts, memberships)

    response = client.get("/research")

    assert response.status_code == 200
    assert "Read-only Research access is available." in response.text
    assert str(USER) not in response.text
    assert str(WORKSPACE) not in response.text
    assert "private-csrf" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert contexts.calls == [USER]
    assert memberships.calls == [(USER, WORKSPACE)]


@pytest.mark.parametrize(
    "context,membership",
    [
        (None, _membership(Permission.RESEARCH_READ)),
        (CONTEXT, None),
        (CONTEXT, _membership()),
        (
            CONTEXT,
            _membership(
                Permission.RESEARCH_READ,
                status=MembershipStatus.INACTIVE,
            ),
        ),
    ],
)
def test_absence_and_denial_share_one_empty_not_found(
    context: CurrentWorkspaceContext | None,
    membership: WorkspaceMembership | None,
) -> None:
    client, _ = _client(Contexts(context), Memberships(membership))

    response = client.get("/research")

    assert response.status_code == 404
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"


def test_absent_context_stops_before_membership_lookup() -> None:
    memberships = Memberships(_membership(Permission.RESEARCH_READ))
    client, _ = _client(Contexts(None), memberships)

    assert client.get("/research").status_code == 404
    assert memberships.calls == []


def test_technical_unavailability_uses_existing_detail_free_outcome() -> None:
    memberships = Memberships(None)
    memberships.error = WorkspaceMembershipStoreUnavailable()
    client, _ = _client(Contexts(CONTEXT), memberships)

    response = client.get("/research", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login/unavailable"
    assert response.headers.get("set-cookie") is None
    assert response.content == b""


@pytest.mark.parametrize(
    "method,path,expected",
    [
        ("post", "/research", 405),
        ("get", "/research?workspace=caller-selected", 400),
    ],
)
def test_rejected_input_stops_before_all_lookups(
    method: str,
    path: str,
    expected: int,
) -> None:
    contexts = Contexts(CONTEXT)
    memberships = Memberships(_membership(Permission.RESEARCH_READ))
    client, sessions = _client(contexts, memberships)

    response = getattr(client, method)(path)

    assert response.status_code == expected
    assert response.content == b""
    assert sessions.calls == []
    assert contexts.calls == []
    assert memberships.calls == []


def test_authorized_landing_links_only_to_fixed_research_path() -> None:
    client, _ = _client(
        Contexts(CONTEXT),
        Memberships(_membership(Permission.RESEARCH_READ)),
    )

    response = client.get("/")

    assert response.status_code == 200
    assert '<a href="/research">Open Research</a>' in response.text
