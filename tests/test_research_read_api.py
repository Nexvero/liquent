from __future__ import annotations

from fastapi.testclient import TestClient

from liquent.backtesting.runner import BacktestResult
from liquent_platform.application.experiment import ExperimentSnapshot, freeze_parameters
from liquent_platform.configuration import PlatformSettings
from liquent_platform.identity.research import ExperimentId, JobId, StrategyVersionId
from liquent_platform.jobs.in_memory import InMemoryResearchJob, InMemoryResearchJobs
from liquent_platform.transport.http.app import create_app


class NoSignalRunner:
    def run(self) -> BacktestResult:
        return BacktestResult(
            experiment_id="runner-result-1",
            number_of_trades=0,
            approved_signals=0,
            rejected_signals=0,
            starting_equity=1_000.0,
            ending_equity=1_000.0,
            equity_curve=(1_000.0,),
            metrics={"number_of_trades": 0.0},
            trades=(),
            parameters={
                "strategy": "NoSignalStrategy",
                "sizing_mode": "absolute",
                "live_execution": False,
                "network_calls": False,
                "paper_trading": False,
            },
        )


def _job() -> InMemoryResearchJob:
    snapshot = ExperimentSnapshot(
        experiment_id=ExperimentId("experiment-1"),
        title="No-signal evidence",
        dataset_ref="synthetic/no-signal",
        dataset_fingerprint="sha256:dataset-1",
        strategy_version_id=StrategyVersionId("strategy-version-1"),
        strategy_parameters=freeze_parameters({"lookback": 3}),
        risk_parameters=freeze_parameters({"sizing_mode": "absolute"}),
        cost_parameters=freeze_parameters({"fee_rate": 0.0}),
    )
    return InMemoryResearchJob(JobId("job-1"), snapshot)


def _client(jobs: InMemoryResearchJobs) -> TestClient:
    app = create_app(
        PlatformSettings(_secrets_dir=None),
        research_jobs=jobs,
    )
    return TestClient(app)


def test_ready_job_status_has_no_evidence_link() -> None:
    jobs = InMemoryResearchJobs()
    jobs.add(_job())

    with _client(jobs) as client:
        response = client.get("/v1/research/jobs/job-1")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-1",
        "experiment_id": "experiment-1",
        "status": "ready",
        "error_code": None,
        "evidence_url": None,
    }


def test_succeeded_job_exposes_existing_no_signal_evidence() -> None:
    jobs = InMemoryResearchJobs()
    job = _job()
    job.execute(NoSignalRunner())
    jobs.add(job)

    with _client(jobs) as client:
        status_response = client.get("/v1/research/jobs/job-1")
        evidence_response = client.get("/v1/research/jobs/job-1/evidence")

    assert status_response.json()["evidence_url"] == (
        "/v1/research/jobs/job-1/evidence"
    )
    assert evidence_response.status_code == 200
    assert evidence_response.json()["title"] == "No-signal evidence"
    assert evidence_response.json()["number_of_trades"] == 0


def test_unknown_job_has_neutral_not_found_error() -> None:
    with _client(InMemoryResearchJobs()) as client:
        response = client.get("/v1/research/jobs/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "research_job_not_found"}


def test_unfinished_job_has_no_partial_evidence() -> None:
    jobs = InMemoryResearchJobs()
    jobs.add(_job())

    with _client(jobs) as client:
        response = client.get("/v1/research/jobs/job-1/evidence")

    assert response.status_code == 404
    assert response.json() == {"detail": "research_evidence_not_found"}
