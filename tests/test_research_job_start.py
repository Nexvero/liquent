from __future__ import annotations

import pytest

from liquent.backtesting.runner import BacktestResult
from liquent_platform.application.experiment import ExperimentSnapshot, freeze_parameters
from liquent_platform.application.start_research import (
    resolve_and_start_research_job,
    start_research_job,
)
from liquent_platform.identity.research import ExperimentId, JobId, StrategyVersionId
from liquent_platform.jobs.in_memory import InMemoryResearchJob, InMemoryResearchJobs
from liquent_platform.jobs.lifecycle import ResearchJobStatus


def _job(job_id: str) -> InMemoryResearchJob:
    snapshot = ExperimentSnapshot(
        experiment_id=ExperimentId("experiment-1"),
        title="Controlled run",
        dataset_ref="synthetic/controlled",
        dataset_fingerprint="sha256:dataset-1",
        strategy_version_id=StrategyVersionId("strategy-version-1"),
        strategy_parameters=freeze_parameters({"lookback": 3}),
        risk_parameters=freeze_parameters({"sizing_mode": "absolute"}),
        cost_parameters=freeze_parameters({"fee_rate": 0.0}),
    )
    return InMemoryResearchJob(JobId(job_id), snapshot)


class SuccessfulRunner:
    calls = 0

    def run(self) -> BacktestResult:
        self.calls += 1
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


class FailingRunner:
    def run(self) -> BacktestResult:
        raise RuntimeError("private runner detail")


class Resolver:
    def __init__(self, runner: SuccessfulRunner) -> None:
        self.runner = runner
        self.snapshot: ExperimentSnapshot | None = None

    def resolve(self, snapshot: ExperimentSnapshot) -> SuccessfulRunner:
        self.snapshot = snapshot
        return self.runner


class FailingResolver:
    def resolve(self, snapshot: ExperimentSnapshot) -> SuccessfulRunner:
        raise ValueError(f"unsupported dataset: {snapshot.dataset_ref}")


def test_start_registers_job_and_returns_terminal_success() -> None:
    jobs = InMemoryResearchJobs()
    job = _job("job-1")

    result = start_research_job(job, SuccessfulRunner(), jobs)

    assert result is job
    assert jobs.get(JobId("job-1")) is job
    assert job.status is ResearchJobStatus.SUCCEEDED


def test_failed_execution_remains_registered_and_neutral() -> None:
    jobs = InMemoryResearchJobs()
    job = _job("job-2")

    start_research_job(job, FailingRunner(), jobs)

    assert jobs.get(JobId("job-2")) is job
    assert job.status is ResearchJobStatus.FAILED
    assert job.error_code == "execution_failed"


def test_duplicate_job_is_rejected_before_runner_execution() -> None:
    jobs = InMemoryResearchJobs()
    jobs.add(_job("job-3"))
    runner = SuccessfulRunner()

    with pytest.raises(ValueError, match="research job already exists: job-3"):
        start_research_job(_job("job-3"), runner, jobs)

    assert runner.calls == 0


def test_resolver_receives_exact_snapshot_before_existing_start_path() -> None:
    jobs = InMemoryResearchJobs()
    job = _job("job-4")
    resolver = Resolver(SuccessfulRunner())

    result = resolve_and_start_research_job(job, resolver, jobs)

    assert resolver.snapshot is job.snapshot
    assert result.status is ResearchJobStatus.SUCCEEDED
    assert jobs.get(JobId("job-4")) is result


def test_resolution_failure_does_not_register_partial_job() -> None:
    jobs = InMemoryResearchJobs()

    with pytest.raises(ValueError, match="unsupported dataset"):
        resolve_and_start_research_job(_job("job-5"), FailingResolver(), jobs)

    with pytest.raises(KeyError, match="research job not found: job-5"):
        jobs.get(JobId("job-5"))
