from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from liquent_platform.application.local_csv import LocalCsvMidBreakoutV0Resolver
from liquent_platform.configuration import PlatformSettings
from liquent_platform.identity.access import (
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
from liquent_platform.jobs.in_memory import InMemoryResearchJobs
from liquent_platform.transport.http.app import create_app


FIXTURES = Path(__file__).parent / "fixtures"
CSV_PATH = FIXTURES / "ohlcv_valid.csv"


def _request(**changes: object) -> dict[str, object]:
    request: dict[str, object] = {
        "job_id": "job-1",
        "experiment_id": "experiment-1",
        "workspace_id": "workspace-1",
        "title": "Local CSV run",
        "dataset_ref": CSV_PATH.name,
        "dataset_fingerprint": (
            f"sha256:{hashlib.sha256(CSV_PATH.read_bytes()).hexdigest()}"
        ),
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
    request.update(changes)
    return request


class StubMembershipLookup:
    def __init__(self, permissions: frozenset[Permission]) -> None:
        self.permissions = permissions

    def get_membership(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> WorkspaceMembership:
        return WorkspaceMembership(
            user_id=user_id,
            workspace_id=workspace_id,
            status=MembershipStatus.ACTIVE,
            permissions=self.permissions,
        )


class StubBrowserSessionLookup:
    def __init__(self, session: ResolvedBrowserSession) -> None:
        self.session = session

    def get_session(self, session_id: SessionId) -> ResolvedBrowserSession | None:
        if session_id == SessionId("opaque-session"):
            return self.session
        return None


def _client(
    *,
    resolver: bool = True,
    permissions: frozenset[Permission] | None = None,
) -> TestClient:
    jobs = InMemoryResearchJobs()
    app = create_app(
        PlatformSettings(_secrets_dir=None),
        research_jobs=jobs,
        research_resolver=(
            LocalCsvMidBreakoutV0Resolver(FIXTURES) if resolver else None
        ),
        research_sessions=(
            StubBrowserSessionLookup(
                ResolvedBrowserSession(
                    SessionPrincipal(UserId("user-1")),
                    "session-proof",
                )
            )
            if permissions is not None
            else None
        ),
        research_memberships=(
            StubMembershipLookup(permissions) if permissions is not None else None
        ),
    )
    return TestClient(app)


def _set_session_cookie(
    client: TestClient, value: str = "opaque-session"
) -> None:
    client.cookies.set("liquent_session", value)


def test_start_route_is_absent_without_explicit_resolver() -> None:
    with _client(resolver=False) as client:
        response = client.post("/v1/research/jobs", json=_request())

    assert response.status_code == 404


def test_start_accepts_complete_snapshot_and_exposes_evidence() -> None:
    with _client() as client:
        start_response = client.post("/v1/research/jobs", json=_request())
        evidence_response = client.get("/v1/research/jobs/job-1/evidence")

    assert start_response.status_code == 202
    assert start_response.json() == {
        "job_id": "job-1",
        "experiment_id": "experiment-1",
        "status": "succeeded",
        "error_code": None,
        "evidence_url": "/v1/research/jobs/job-1/evidence",
    }
    assert evidence_response.status_code == 200
    assert evidence_response.json()["title"] == "Local CSV run"
    assert evidence_response.json()["metrics"]["profit_factor"] is None


def test_unresolvable_input_is_neutral_and_leaves_no_job() -> None:
    with _client() as client:
        response = client.post(
            "/v1/research/jobs",
            json=_request(dataset_fingerprint="sha256:wrong"),
        )
        status_response = client.get("/v1/research/jobs/job-1")

    assert response.status_code == 422
    assert response.json() == {"detail": "research_inputs_unresolvable"}
    assert status_response.status_code == 404


def test_duplicate_job_returns_conflict_without_overwrite() -> None:
    with _client() as client:
        first = client.post("/v1/research/jobs", json=_request())
        duplicate = client.post("/v1/research/jobs", json=_request())
        status_response = client.get("/v1/research/jobs/job-1")

    assert first.status_code == 202
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "research_job_conflict"}
    assert status_response.json()["status"] == "succeeded"


def test_request_does_not_coerce_parameter_strings() -> None:
    request = _request()
    strategy = dict(request["strategy_parameters"])  # type: ignore[arg-type]
    strategy["allow_short"] = "false"
    request["strategy_parameters"] = strategy

    with _client() as client:
        response = client.post("/v1/research/jobs", json=request)

    assert response.status_code == 422


def test_authorized_start_accepts_research_write_permission() -> None:
    with _client(permissions=frozenset({Permission.RESEARCH_WRITE})) as client:
        _set_session_cookie(client)
        response = client.post(
            "/v1/research/jobs",
            json=_request(),
            headers={"X-CSRF-Token": "session-proof"},
        )

    assert response.status_code == 202
    assert response.json()["status"] == "succeeded"


def test_authorized_start_rejects_read_only_without_registering_job() -> None:
    with _client(permissions=frozenset({Permission.RESEARCH_READ})) as client:
        _set_session_cookie(client)
        denied = client.post(
            "/v1/research/jobs",
            json=_request(),
            headers={"X-CSRF-Token": "session-proof"},
        )
        missing = client.get("/v1/research/jobs/job-1")

    assert denied.status_code == 403
    assert denied.json() == {"detail": "permission_denied"}
    assert missing.status_code == 404


def test_session_bound_start_requires_matching_csrf_header() -> None:
    with _client(permissions=frozenset({Permission.RESEARCH_WRITE})) as client:
        _set_session_cookie(client)
        missing_header = client.post(
            "/v1/research/jobs",
            json=_request(),
        )
        wrong_header = client.post(
            "/v1/research/jobs",
            json=_request(),
            headers={"X-CSRF-Token": "wrong-proof"},
        )
        missing_job = client.get("/v1/research/jobs/job-1")

    assert missing_header.status_code == wrong_header.status_code == 403
    assert missing_header.json() == wrong_header.json() == {
        "detail": "csrf_validation_failed"
    }
    assert missing_job.status_code == 404


def test_session_bound_start_requires_known_session_cookie() -> None:
    with _client(permissions=frozenset({Permission.RESEARCH_WRITE})) as client:
        missing = client.post(
            "/v1/research/jobs",
            json=_request(),
            headers={"X-CSRF-Token": "session-proof"},
        )
        _set_session_cookie(client, "unknown-session")
        unknown = client.post(
            "/v1/research/jobs",
            json=_request(),
            headers={"X-CSRF-Token": "session-proof"},
        )

    assert missing.status_code == unknown.status_code == 401
    assert missing.json() == unknown.json() == {
        "detail": "authentication_required"
    }
