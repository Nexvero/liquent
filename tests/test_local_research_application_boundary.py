from __future__ import annotations

from liquent.backtesting.runner import BacktestResult
from liquent_platform.application.research import execute_local_research


def _result() -> BacktestResult:
    return BacktestResult(
        experiment_id="experiment-1",
        number_of_trades=0,
        approved_signals=0,
        rejected_signals=0,
        starting_equity=10_000.0,
        ending_equity=10_000.0,
        equity_curve=(10_000.0,),
        metrics={"number_of_trades": 0.0},
        trades=(),
        parameters={
            "strategy": "ExampleStrategy",
            "sizing_mode": "absolute",
            "live_execution": False,
            "network_calls": False,
            "paper_trading": False,
        },
    )


class StubRunner:
    def __init__(self) -> None:
        self.calls = 0

    def run(self) -> BacktestResult:
        self.calls += 1
        return _result()


def test_boundary_runs_once_and_returns_existing_neutral_summary() -> None:
    runner = StubRunner()

    summary = execute_local_research(runner, title="No-signal research run")

    assert runner.calls == 1
    assert summary.experiment_id == "experiment-1"
    assert summary.title == "No-signal research run"
    assert summary.number_of_trades == 0
    assert summary.approved_signals == 0
    assert summary.safety_flags == {
        "live_execution": False,
        "network_calls": False,
        "paper_trading": False,
    }


def test_boundary_does_not_treat_no_signals_as_failure() -> None:
    summary = execute_local_research(StubRunner(), title="Empty evidence")

    assert summary.number_of_trades == 0
    assert summary.ending_equity == summary.starting_equity
    assert "recommend" not in " ".join(summary.risk_notes).lower()
