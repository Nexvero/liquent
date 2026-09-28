from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from liquent_platform.application.internal_destination import (
    ValidatedInternalDestination,
)
from liquent_platform.identity.access import CurrentWorkspaceContext, UserId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import (
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipStoreUnavailable,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.transport.http.app import create_app

USER = UserId("internal-user-2657")
WORKSPACE = WorkspaceId("internal-workspace-2657")


class Sessions:
    def get_session(self, session_id: SessionId) -> ResolvedBrowserSession | None:
        return ResolvedBrowserSession(
            principal=SessionPrincipal(USER), expected_csrf_token="private-csrf"
        )


class RecordingContexts:
    def __init__(self, result: CurrentWorkspaceContext | None) -> None:
        self.result = result
        self.error: Exception | None = None
        self.calls: list[UserId] = []

    def resolve_current_workspace(
        self, user_id: UserId
    ) -> CurrentWorkspaceContext | None:
        self.calls.append(user_id)
        if self.error is not None:
            raise self.error
        return self.result


def _client(
    contexts: RecordingContexts | None, *, database_engine: Engine | None = None
) -> TestClient:
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
    }
    if contexts is not None:
        dependencies["landing_workspace_contexts"] = contexts
    if database_engine is not None:
        dependencies["database_engine"] = database_engine
    client = TestClient(create_app(**dependencies))
    client.cookies.set("liquent_session", "opaque-session")
    return client


def test_unique_current_workspace_is_confirmed_without_identifiers() -> None:
    contexts = RecordingContexts(CurrentWorkspaceContext(USER, WORKSPACE))
    response = _client(contexts).get("/")

    assert response.status_code == 200
    assert "Your workspace context is available." in response.text
    assert str(USER) not in response.text
    assert str(WORKSPACE) not in response.text
    assert "private-csrf" not in response.text
    assert contexts.calls == [USER]


def test_absent_or_ambiguous_context_has_one_neutral_document() -> None:
    contexts = RecordingContexts(None)
    response = _client(contexts).get("/")

    assert response.status_code == 200
    assert "No workspace context is available." in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert contexts.calls == [USER]


def test_context_store_unavailability_uses_existing_detail_free_outcome() -> None:
    contexts = RecordingContexts(None)
    contexts.error = WorkspaceMembershipStoreUnavailable()
    response = _client(contexts).get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login/unavailable"
    assert response.headers.get("set-cookie") is None
    assert response.content == b""


def test_rejected_input_does_not_resolve_workspace_context() -> None:
    contexts = RecordingContexts(CurrentWorkspaceContext(USER, WORKSPACE))
    response = _client(contexts).get("/?workspace=caller-selected")

    assert response.status_code == 400
    assert response.content == b""
    assert contexts.calls == []


def test_database_app_composes_current_workspace_resolver(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'landing.db'}")
    upgrade_to_head(str(engine.url))
    try:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO identity_users VALUES (:user,'active')"),
                {"user": USER.encode()},
            )
            connection.execute(
                text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
                {"workspace": WORKSPACE.encode()},
            )
            connection.execute(
                text(
                    "INSERT INTO workspace_memberships"
                    " VALUES (:user,:workspace,'active',NULL)"
                ),
                {"user": USER.encode(), "workspace": WORKSPACE.encode()},
            )
        response = _client(None, database_engine=engine).get("/")
        assert response.status_code == 200
        assert "Your workspace context is available." in response.text
        assert str(WORKSPACE) not in response.text
    finally:
        engine.dispose()
