from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from liquent_platform.application.internal_destination import (
    ValidatedInternalDestination,
)
from liquent_platform.configuration import PlatformSettings
from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.persistence.browser_sessions import DatabaseBrowserSessions
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.research_jobs import DatabaseResearchJobs
from liquent_platform.transport.http.app import create_app

NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
USER = UserId("wired-index-user")
WORKSPACE = WorkspaceId("wired-index-workspace")
SESSION = SessionId("wired-index-session")


def _app(engine, **overrides):
    dependencies = {
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
        "database_engine": engine,
    }
    dependencies.update(overrides)
    return create_app(PlatformSettings(_secrets_dir=None), **dependencies)


def _seed(engine) -> None:
    sessions = DatabaseBrowserSessions(engine, now=lambda: NOW)
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
                " (user_id,workspace_id,status) VALUES"
                " (:user,:workspace,'active')"
            ),
            {"user": USER.encode(), "workspace": WORKSPACE.encode()},
        )
        connection.execute(
            text(
                "INSERT INTO workspace_membership_permissions VALUES"
                " (:user,:workspace,'research:read')"
            ),
            {"user": USER.encode(), "workspace": WORKSPACE.encode()},
        )
        connection.execute(
            text(
                "INSERT INTO research_jobs VALUES"
                " (:job,:revision,:actor,:workspace,'{}','backtest_result_v1',"
                " 'queued',:accepted,:updated)"
            ),
            {
                "job": b"wired-job",
                "revision": b"wired-revision",
                "actor": USER.encode(),
                "workspace": WORKSPACE.encode(),
                "accepted": NOW,
                "updated": NOW,
            },
        )
    assert sessions.add_session(
        SESSION,
        BrowserSessionRecord(
            ResolvedBrowserSession(SessionPrincipal(USER), "wired-csrf"),
            NOW + timedelta(hours=1),
        ),
    )


def test_database_engine_wires_persistent_workspace_index(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'wired-index.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
    _seed(engine)
    try:
        app = _app(engine)

        assert type(app.state.workspace_research_job_index) is DatabaseResearchJobs
        with TestClient(app) as client:
            client.cookies.set("liquent_session", str(SESSION))
            response = client.get("/research")

        assert response.status_code == 200
        assert "wired-job" in response.text
        assert str(USER) not in response.text
        assert str(WORKSPACE) not in response.text
    finally:
        engine.dispose()


def test_committed_revocation_affects_next_persistent_page(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'wired-revocation.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
    _seed(engine)
    try:
        app = _app(engine)
        with TestClient(app) as client:
            client.cookies.set("liquent_session", str(SESSION))
            assert client.get("/research").status_code == 200
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM workspace_membership_permissions")
                )
            denied = client.get("/research")

        assert denied.status_code == 404
        assert denied.content == b""
    finally:
        engine.dispose()


def test_explicit_index_dependency_keeps_precedence(tmp_path: Path) -> None:
    class ExplicitIndex:
        def list_jobs(self, actor_user_id, workspace_id):
            return ()

    explicit = ExplicitIndex()
    engine = build_engine(f"sqlite:///{tmp_path / 'precedence.db'}")
    try:
        app = _app(engine, workspace_research_job_index=explicit)
        assert app.state.workspace_research_job_index is explicit
    finally:
        engine.dispose()
