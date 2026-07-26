"""Minimal application boundary for deterministic local research."""

from __future__ import annotations

from typing import Protocol

from liquent.backtesting.reporting import (
    BacktestExperimentSummary,
    summarize_backtest_result,
)
from liquent.backtesting.runner import BacktestResult


class BacktestExecution(Protocol):
    """The one capability the product workflow needs from a backtest runner."""

    def run(self) -> BacktestResult: ...


def execute_local_research(
    runner: BacktestExecution, *, title: str
) -> BacktestExperimentSummary:
    """Execute one deterministic research run and return neutral evidence."""

    result = runner.run()
    return summarize_backtest_result(result, title=title)
