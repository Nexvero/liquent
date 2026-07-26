from __future__ import annotations

import pytest

from liquent.backtesting.runner import BacktestResult
from liquent_platform.identity.research import ExperimentId
from liquent_platform.jobs.in_memory import InMemoryResearchJob
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


def test_ready_job_completes_with_existing_evidence() -> None:
    job = InMemoryResearchJob(ExperimentId("experiment-1"), "No-signal run")

    job.execute(SuccessfulRunner())

    assert job.status is ResearchJobStatus.SUCCEEDED
    assert job.error_code is None
    assert job.evidence is not None
    assert job.evidence.title == "No-signal run"
    assert job.evidence.number_of_trades == 0


def test_runner_failure_is_terminal_and_does_not_expose_internal_message() -> None:
    job = InMemoryResearchJob(ExperimentId("experiment-2"), "Failure run")

    job.execute(FailingRunner())

    assert job.status is ResearchJobStatus.FAILED
    assert job.evidence is None
    assert job.error_code == "execution_failed"


def test_terminal_job_cannot_be_executed_again() -> None:
    job = InMemoryResearchJob(ExperimentId("experiment-3"), "One run only")
    job.execute(SuccessfulRunner())

    with pytest.raises(ValueError, match="invalid research job transition"):
        job.execute(SuccessfulRunner())
