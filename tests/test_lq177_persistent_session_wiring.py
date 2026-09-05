from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from liquent_platform.configuration import PlatformSettings
from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.persistence.browser_sessions import DatabaseBrowserSessions
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.transport.http.app import create_app

NOW = datetime.now(UTC)
SESSION = SessionId("session-177")


def test_injected_database_engine_wires_persistent_logout_without_ownership(
    tmp_path: Path,
) -> None:
    url = f"sqlite:///{tmp_path / 'runtime.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES (:user,'active')"
        ), {"user": b"user-177"})
    sessions = DatabaseBrowserSessions(engine, now=lambda: NOW)
    assert sessions.add_session(
        SESSION,
        BrowserSessionRecord(
            ResolvedBrowserSession(
                SessionPrincipal(UserId("user-177")), "csrf-177"
            ),
            NOW + timedelta(hours=1),
        ),
    ) is True
    app = create_app(
        PlatformSettings(_secrets_dir=None),
        database_engine=engine,
    )

    with TestClient(app) as client:
        client.cookies.set("liquent_session", str(SESSION))
        response = client.post(
            "/v1/session/logout", headers={"X-CSRF-Token": "csrf-177"}
        )

    assert response.status_code == 204
    assert sessions.get_session(SESSION) is None
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT 1")) == 1
    engine.dispose()


def test_database_wiring_does_not_enable_incomplete_oidc_routes(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'closed.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
    try:
        app = create_app(
            PlatformSettings(_secrets_dir=None),
            database_engine=engine,
        )
        paths = {route.path for route in app.routes}
        assert "/v1/session/logout" in paths
        assert "/v1/session/oidc/start" not in paths
        assert "/v1/session/oidc/callback" not in paths
        assert "/v1/research/jobs" not in paths
    finally:
        engine.dispose()


def test_explicit_logout_dependencies_keep_precedence(tmp_path: Path) -> None:
    class Sessions:
        def get_session(self, session_id: SessionId):
            return None

        def revoke_session(self, session_id: SessionId) -> None:
            raise AssertionError("unknown session is not revoked")

    url = f"sqlite:///{tmp_path / 'precedence.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
    try:
        app = create_app(
            PlatformSettings(_secrets_dir=None),
            logout_sessions=Sessions(),
            logout_revocations=Sessions(),
            database_engine=engine,
        )
        with TestClient(app) as client:
            client.cookies.set("liquent_session", "unknown")
            assert client.post("/v1/session/logout").status_code == 204
    finally:
        engine.dispose()
