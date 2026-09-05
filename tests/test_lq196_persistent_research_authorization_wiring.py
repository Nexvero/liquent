from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from liquent_platform.application.experiment import (
    ExperimentSnapshot,
    freeze_parameters,
)
from liquent_platform.configuration import PlatformSettings
from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import (
    ExperimentId,
    JobId,
    StrategyVersionId,
    WorkspaceId,
)
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.jobs.in_memory import InMemoryResearchJob, InMemoryResearchJobs
from liquent_platform.persistence.browser_sessions import DatabaseBrowserSessions
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.transport.http.app import create_app

NOW = datetime.now(UTC)
USER = UserId("user-196")
WORKSPACE = WorkspaceId("workspace-196")
SESSION = SessionId("session-196")


def _job() -> InMemoryResearchJob:
    return InMemoryResearchJob(
        JobId("job-196"),
        ExperimentSnapshot(
            experiment_id=ExperimentId("experiment-196"),
            workspace_id=WORKSPACE,
            title="Protected research",
            dataset_ref="fixture.csv",
            dataset_fingerprint="sha256:fixture",
            strategy_version_id=StrategyVersionId("strategy-196"),
            strategy_parameters=freeze_parameters({}),
            risk_parameters=freeze_parameters({}),
            cost_parameters=freeze_parameters({}),
        ),
    )


def _seed(engine, *, permission: str = "research:read") -> None:
    sessions = DatabaseBrowserSessions(engine, now=lambda: NOW)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:user,'active')"),
            {"user": str(USER).encode()},
        )
        connection.execute(
            text("INSERT INTO identity_workspaces VALUES (:workspace,'active')"),
            {"workspace": str(WORKSPACE).encode()},
        )
        connection.execute(
            text(
                "INSERT INTO workspace_memberships"
                " (user_id,workspace_id,status) VALUES"
                " (:user,:workspace,'active')"
            ),
            {"user": str(USER).encode(), "workspace": str(WORKSPACE).encode()},
        )
        connection.execute(
            text(
                "INSERT INTO workspace_membership_permissions VALUES"
                " (:user,:workspace,:permission)"
            ),
            {
                "user": str(USER).encode(),
                "workspace": str(WORKSPACE).encode(),
                "permission": permission,
            },
        )
    assert sessions.add_session(
        SESSION,
        BrowserSessionRecord(
            ResolvedBrowserSession(SessionPrincipal(USER), "csrf-196"),
            NOW + timedelta(hours=1),
        ),
    )


def test_database_wiring_closes_anonymous_research_read(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'closed.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
    jobs = InMemoryResearchJobs()
    jobs.add(_job())
    try:
        app = create_app(
            PlatformSettings(_secrets_dir=None),
            database_engine=engine,
            research_jobs=jobs,
        )
        with TestClient(app) as client:
            response = client.get("/v1/research/jobs/job-196")
        assert response.status_code == 401
        assert response.json() == {"detail": "authentication_required"}
    finally:
        engine.dispose()


def test_persistent_session_and_membership_authorize_stored_workspace(
    tmp_path: Path,
) -> None:
    url = f"sqlite:///{tmp_path / 'allowed.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
    _seed(engine)
    jobs = InMemoryResearchJobs()
    jobs.add(_job())
    try:
        app = create_app(
            PlatformSettings(_secrets_dir=None),
            database_engine=engine,
            research_jobs=jobs,
        )
        with TestClient(app) as client:
            client.cookies.set("liquent_session", str(SESSION))
            response = client.get("/v1/research/jobs/job-196")
        assert response.status_code == 200
        assert response.json()["job_id"] == "job-196"
    finally:
        engine.dispose()


def test_committed_permission_revocation_hides_later_read(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'revoked.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
    _seed(engine)
    jobs = InMemoryResearchJobs()
    jobs.add(_job())
    try:
        app = create_app(
            PlatformSettings(_secrets_dir=None),
            database_engine=engine,
            research_jobs=jobs,
        )
        with TestClient(app) as client:
            client.cookies.set("liquent_session", str(SESSION))
            assert client.get("/v1/research/jobs/job-196").status_code == 200
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM workspace_membership_permissions"))
            denied = client.get("/v1/research/jobs/job-196")
        assert denied.status_code == 404
        assert denied.json() == {"detail": "research_job_not_found"}
    finally:
        engine.dispose()


def test_explicit_research_dependencies_keep_precedence(tmp_path: Path) -> None:
    class Sessions:
        def get_session(self, session_id: SessionId):
            return None

    class Memberships:
        def get_membership(self, user_id: UserId, workspace_id: WorkspaceId):
            raise AssertionError("missing session must stop first")

    engine = build_engine(f"sqlite:///{tmp_path / 'precedence.db'}")
    try:
        app = create_app(
            PlatformSettings(_secrets_dir=None),
            database_engine=engine,
            research_sessions=Sessions(),
            research_memberships=Memberships(),
        )
        with TestClient(app) as client:
            assert client.get("/v1/research/jobs/missing").status_code == 401
    finally:
        engine.dispose()
