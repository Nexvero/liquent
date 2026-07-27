from __future__ import annotations

import pytest

from liquent.backtesting.runner import BacktestResult
from liquent_platform.application.experiment import ExperimentSnapshot, freeze_parameters
from liquent_platform.identity.research import (
    ExperimentId,
    JobId,
    StrategyVersionId,
    WorkspaceId,
)
from liquent_platform.jobs.in_memory import InMemoryResearchJob, InMemoryResearchJobs
from liquent_platform.jobs.lifecycle import ResearchJobStatus


def _result() -> BacktestResult:
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


class SuccessfulRunner:
    def run(self) -> BacktestResult:
        return _result()


class FailingRunner:
    def run(self) -> BacktestResult:
        raise RuntimeError("internal detail must not become the public error code")


def _snapshot(number: int, title: str) -> ExperimentSnapshot:
    return ExperimentSnapshot(
        experiment_id=ExperimentId(f"experiment-{number}"),
        workspace_id=WorkspaceId("workspace-1"),
        title=title,
        dataset_ref="synthetic/no-signal",
        dataset_fingerprint="sha256:test-dataset",
        strategy_version_id=StrategyVersionId("strategy-version-1"),
        strategy_parameters=freeze_parameters({"lookback_bars": 3}),
        risk_parameters=freeze_parameters({"sizing_mode": "absolute"}),
        cost_parameters=freeze_parameters({"fee_rate": 0.0}),
    )


def test_ready_job_completes_with_existing_evidence() -> None:
    job = InMemoryResearchJob(JobId("job-1"), _snapshot(1, "No-signal run"))

    job.execute(SuccessfulRunner())

    assert job.status is ResearchJobStatus.SUCCEEDED
    assert job.error_code is None
    assert job.evidence is not None
    assert job.evidence.title == "No-signal run"
    assert job.evidence.number_of_trades == 0


def test_runner_failure_is_terminal_and_does_not_expose_internal_message() -> None:
    job = InMemoryResearchJob(JobId("job-2"), _snapshot(2, "Failure run"))

    job.execute(FailingRunner())

    assert job.status is ResearchJobStatus.FAILED
    assert job.evidence is None
    assert job.error_code == "execution_failed"


def test_terminal_job_cannot_be_executed_again() -> None:
    job = InMemoryResearchJob(JobId("job-3"), _snapshot(3, "One run only"))
    job.execute(SuccessfulRunner())

    with pytest.raises(ValueError, match="invalid research job transition"):
        job.execute(SuccessfulRunner())


def test_job_register_adds_and_returns_the_same_job() -> None:
    jobs = InMemoryResearchJobs()
    job = InMemoryResearchJob(JobId("job-4"), _snapshot(4, "Lookup"))

    jobs.add(job)

    assert jobs.get(JobId("job-4")) is job


def test_job_register_rejects_duplicate_identity() -> None:
    jobs = InMemoryResearchJobs()
    first = InMemoryResearchJob(JobId("job-5"), _snapshot(5, "First"))
    duplicate = InMemoryResearchJob(JobId("job-5"), _snapshot(6, "Duplicate"))
    jobs.add(first)

    with pytest.raises(ValueError, match="research job already exists: job-5"):
        jobs.add(duplicate)


def test_job_register_reports_missing_identity() -> None:
    jobs = InMemoryResearchJobs()

    with pytest.raises(KeyError, match="research job not found: missing"):
        jobs.get(JobId("missing"))
