from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from liquent_platform.application.local_csv import LocalCsvMidBreakoutV0Resolver
from liquent_platform.configuration import PlatformSettings
from liquent_platform.jobs.in_memory import InMemoryResearchJobs
from liquent_platform.transport.http.app import create_app


FIXTURES = Path(__file__).parent / "fixtures"
CSV_PATH = FIXTURES / "ohlcv_valid.csv"


def _request(**changes: object) -> dict[str, object]:
    request: dict[str, object] = {
        "job_id": "job-1",
        "experiment_id": "experiment-1",
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


def _client(*, resolver: bool = True) -> TestClient:
    jobs = InMemoryResearchJobs()
    app = create_app(
        PlatformSettings(_secrets_dir=None),
        research_jobs=jobs,
        research_resolver=(
            LocalCsvMidBreakoutV0Resolver(FIXTURES) if resolver else None
        ),
    )
    return TestClient(app)


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
