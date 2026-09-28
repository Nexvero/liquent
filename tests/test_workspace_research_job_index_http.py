from datetime import UTC, datetime, timedelta
from typing import Any

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
from liquent_platform.identity.research import JobId, WorkspaceId
from liquent_platform.identity.research_job import ResearchJobIndexItem
from liquent_platform.identity.session import (
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.jobs.lifecycle import ResearchJobStatus
from liquent_platform.persistence.identity_errors import ResearchJobStoreUnavailable
from liquent_platform.transport.http.app import create_app

USER = UserId("index-http-user")
WORKSPACE = WorkspaceId("index-http-workspace")
NOW = datetime(2026, 9, 15, 10, 30, tzinfo=UTC)


class Sessions:
    def get_session(self, session_id: SessionId):
        return ResolvedBrowserSession(SessionPrincipal(USER), "private-csrf")


class Contexts:
    def __init__(self, result=None):
        self.result = result if result is not None else CurrentWorkspaceContext(
            USER, WORKSPACE
        )

    def resolve_current_workspace(self, user_id):
        return self.result


class Memberships:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def get_membership(self, user_id, workspace_id):
        permissions = (
            frozenset({Permission.RESEARCH_READ}) if self.allowed else frozenset()
        )
        return WorkspaceMembership(
            USER, WORKSPACE, MembershipStatus.ACTIVE, permissions
        )


class Index:
    def __init__(self, result=(), error=None):
        self.result = result
        self.error = error
        self.calls = []

    def list_jobs(self, actor_user_id, workspace_id):
        self.calls.append((actor_user_id, workspace_id))
        if self.error is not None:
            raise self.error
        return self.result


def _client(index, *, memberships=None):
    sessions = Sessions()
    dependencies: dict[str, Any] = {
        "oidc_callback_transactions": object(),
        "oidc_callback_verifier": object(),
        "oidc_callback_identities": object(),
        "oidc_callback_admissions": object(),
        "oidc_callback_sessions": object(),
        "oidc_callback_material": object(),
        "oidc_login_clock": lambda: NOW,
        "oidc_session_lifetime": timedelta(hours=1),
        "oidc_callback_rejection": ValidatedInternalDestination("/login/rejected"),
        "oidc_callback_unavailable": ValidatedInternalDestination(
            "/login/unavailable"
        ),
        "logout_sessions": sessions,
        "logout_revocations": object(),
        "landing_workspace_contexts": Contexts(),
        "research_sessions": sessions,
        "research_memberships": memberships or Memberships(),
        "workspace_research_job_index": index,
    }
    client = TestClient(create_app(**dependencies))
    client.cookies.set("liquent_session", "opaque-session")
    return client


def test_authorized_index_renders_only_minimum_read_facts() -> None:
    item = ResearchJobIndexItem(
        JobId("job-visible"), ResearchJobStatus.RUNNING, NOW, NOW
    )
    index = Index((item,))

    response = _client(index).get("/research")

    assert response.status_code == 200
    assert "Research jobs" in response.text
    assert "job-visible" in response.text
    assert "running" in response.text
    assert NOW.isoformat() in response.text
    assert str(USER) not in response.text
    assert str(WORKSPACE) not in response.text
    assert "private-csrf" not in response.text
    assert "href=\"/v1/research/jobs/" not in response.text
    assert index.calls == [(USER, WORKSPACE)]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_authorized_empty_renders_successful_empty_state() -> None:
    response = _client(Index()).get("/research")

    assert response.status_code == 200
    assert "No Research jobs are available." in response.text
    assert "<ol>" not in response.text


def test_denial_remains_detail_free_and_skips_index() -> None:
    index = Index()

    response = _client(index, memberships=Memberships(allowed=False)).get(
        "/research"
    )

    assert response.status_code == 404
    assert response.content == b""
    assert index.calls == []


def test_index_unavailability_redirects_without_partial_document() -> None:
    response = _client(Index(error=ResearchJobStoreUnavailable())).get(
        "/research", follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login/unavailable"
    assert response.content == b""
    assert response.headers.get("set-cookie") is None


def test_rejected_query_never_reads_index() -> None:
    index = Index()

    response = _client(index).get("/research?limit=100")

    assert response.status_code == 400
    assert index.calls == []
