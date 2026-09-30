from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from liquent_platform.application.local_csv import LocalCsvMidBreakoutV0Resolver
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
from liquent_platform.transport.http.app import create_app


USER = UserId("lq2771-user")
WORKSPACE = WorkspaceId("lq2771-workspace")
SESSION = SessionId("lq2771-session")
CSRF = "lq2771-csrf"
CSV = Path(__file__).parent / "fixtures" / "ohlcv_valid.csv"


def _request(job_id: str) -> dict[str, object]:
    return {
        "job_id": job_id,
        "experiment_id": f"{job_id}-experiment",
        "workspace_id": str(WORKSPACE),
        "title": "Persistent staging proof",
        "dataset_ref": CSV.name,
        "dataset_fingerprint": f"sha256:{hashlib.sha256(CSV.read_bytes()).hexdigest()}",
        "strategy_version_id": "mid-breakout-v0",
        "strategy_parameters": {
            "lookback_bars": 1,
            "stop_distance_pct": 0.05,
            "min_strength": 0.0,
            "allow_short": True,
        },
        "risk_parameters": {
            "initial_equity": 1_000.0,
            "max_position_size": 10.0,
            "max_total_exposure": 100.0,
            "risk_per_trade": 5.0,
            "max_daily_drawdown": 1_000.0,
            "sizing_mode": "absolute",
        },
        "cost_parameters": {"fee_rate": 0.0, "spread": 0.0, "slippage": 0.0},
    }


def test_database_backed_start_queues_for_worker_and_honors_revocation(
    tmp_path: Path,
) -> None:
    url = f"sqlite:///{tmp_path / 'lq2771.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
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
            connection.execute(text(
                "INSERT INTO workspace_memberships"
                " (user_id,workspace_id,status) VALUES"
                " (:user,:workspace,'active')"
            ), {"user": USER.encode(), "workspace": WORKSPACE.encode()})
            connection.execute(text(
                "INSERT INTO workspace_membership_permissions VALUES"
                " (:user,:workspace,'research:write')"
            ), {"user": USER.encode(), "workspace": WORKSPACE.encode()})
            connection.execute(text(
                "INSERT INTO workspace_membership_permissions VALUES"
                " (:user,:workspace,'research:read')"
            ), {"user": USER.encode(), "workspace": WORKSPACE.encode()})

        sessions = DatabaseBrowserSessions(engine, now=lambda: datetime.now(UTC))
        assert sessions.add_session(
            SESSION,
            BrowserSessionRecord(
                ResolvedBrowserSession(SessionPrincipal(USER), CSRF),
                datetime(2099, 1, 1, tzinfo=UTC),
            ),
        )
        app = create_app(
            PlatformSettings(_secrets_dir=None),
            database_engine=engine,
            research_resolver=LocalCsvMidBreakoutV0Resolver(CSV.parent),
        )
        assert app.state.persistent_research_jobs is not None

        with TestClient(app) as client:
            client.cookies.set("liquent_session", str(SESSION))
            accepted = client.post(
                "/v1/research/jobs",
                headers={"X-CSRF-Token": CSRF},
                json=_request("lq2771-acceptance"),
            )
            assert accepted.status_code == 202
            payload = accepted.json()
            assert payload["status"] == "queued"
            assert payload["job_id"] != "lq2771-acceptance"
            durable_job_id = payload["job_id"]
            status = client.get(f"/v1/research/jobs/{payload['job_id']}")
            assert status.status_code == 200
            assert status.json()["experiment_id"] == "lq2771-acceptance-experiment"

            with engine.begin() as connection:
                connection.execute(text(
                    "UPDATE research_jobs SET status='succeeded' WHERE job_id=:job"
                ), {"job": durable_job_id.encode()})
                connection.execute(text(
                    "INSERT INTO research_job_outcomes VALUES "
                    "(:job,'succeeded',:summary,'artifact.json',:sha,"
                    "'application/json',2,NULL,:completed)"
                ), {
                    "job": durable_job_id.encode(),
                    "summary": '{"experiment_id":"lq2771-acceptance-experiment"}',
                    "sha": "a" * 64,
                    "completed": datetime.now(UTC),
                })

            evidence = client.get(f"/v1/research/jobs/{durable_job_id}/evidence")
            assert evidence.status_code == 200
            assert evidence.json() == {
                "experiment_id": "lq2771-acceptance-experiment"
            }

            with engine.begin() as connection:
                assert connection.scalar(text("SELECT count(*) FROM research_jobs")) == 1
                connection.execute(text(
                    "DELETE FROM workspace_membership_permissions"
                ))

            denied = client.post(
                "/v1/research/jobs",
                headers={"X-CSRF-Token": CSRF},
                json=_request("lq2771-denied"),
            )
            assert denied.status_code == 403
            assert denied.json() == {"detail": "permission_denied"}
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT count(*) FROM research_jobs")) == 1
    finally:
        engine.dispose()


def test_authorization_precedes_persistent_dataset_resolution(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'lq2771-auth-order.db'}"
    upgrade_to_head(url)
    engine = build_engine(url)
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
            connection.execute(text(
                "INSERT INTO workspace_memberships"
                " (user_id,workspace_id,status) VALUES"
                " (:user,:workspace,'active')"
            ), {"user": USER.encode(), "workspace": WORKSPACE.encode()})

        sessions = DatabaseBrowserSessions(engine, now=lambda: datetime.now(UTC))
        assert sessions.add_session(
            SESSION,
            BrowserSessionRecord(
                ResolvedBrowserSession(SessionPrincipal(USER), CSRF),
                datetime(2099, 1, 1, tzinfo=UTC),
            ),
        )
        app = create_app(
            PlatformSettings(_secrets_dir=None),
            database_engine=engine,
            research_resolver=LocalCsvMidBreakoutV0Resolver(CSV.parent),
        )
        invalid = _request("lq2771-invalid-dataset")
        invalid["dataset_ref"] = "missing.csv"

        with TestClient(app) as client:
            client.cookies.set("liquent_session", str(SESSION))
            denied = client.post(
                "/v1/research/jobs",
                headers={"X-CSRF-Token": CSRF},
                json=invalid,
            )
            assert denied.status_code == 403
            assert denied.json() == {"detail": "permission_denied"}
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT count(*) FROM research_jobs")) == 0
    finally:
        engine.dispose()
