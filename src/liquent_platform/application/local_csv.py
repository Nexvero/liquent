"""One explicit local CSV resolver for the first research product slice."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from liquent.backtesting.runner import BacktestResult, BacktestRunner, CostModel
from liquent.data.sources import HistoricalFileSource
from liquent.risk.engine import RiskEngine, RiskLimits
from liquent.strategy import MidBreakoutStrategy
from liquent_platform.application.experiment import ExperimentSnapshot, ParameterSet


_STRATEGY_KEYS = {
    "allow_short",
    "lookback_bars",
    "min_strength",
    "stop_distance_pct",
}
_RISK_KEYS = {
    "initial_equity",
    "max_daily_drawdown",
    "max_position_size",
    "max_total_exposure",
    "risk_per_trade",
    "sizing_mode",
}
_COST_KEYS = {"fee_rate", "slippage", "spread"}


class _SnapshotBoundBacktestExecution:
    """Bind runner evidence to the accepted persistent experiment identity."""

    __slots__ = ("_runner", "_experiment_id")

    def __init__(self, runner: BacktestRunner, experiment_id: str) -> None:
        self._runner = runner
        self._experiment_id = experiment_id

    def run(self) -> BacktestResult:
        return replace(self._runner.run(), experiment_id=self._experiment_id)


def _exact_parameters(
    name: str, parameters: ParameterSet, expected: set[str]
) -> dict[str, str | int | float | bool]:
    values = dict(parameters)
    if set(values) != expected:
        raise ValueError(f"{name} must contain exactly: {', '.join(sorted(expected))}")
    return values


def _number(values: dict[str, object], key: str) -> float:
    value = values[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric")
    return float(value)


def _integer(values: dict[str, object], key: str) -> int:
    value = values[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


class LocalCsvMidBreakoutV0Resolver:
    """Resolve only allowlisted local CSV + MidBreakout v0 snapshots."""

    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root.resolve(strict=True)

    def resolve(self, snapshot: ExperimentSnapshot) -> BacktestRunner:
        if snapshot.strategy_version_id != "mid-breakout-v0":
            raise ValueError("unsupported strategy version")

        csv_path = (self.data_root / snapshot.dataset_ref).resolve(strict=True)
        if self.data_root not in csv_path.parents or not csv_path.is_file():
            raise ValueError("dataset must be a file below the configured data root")
        fingerprint = f"sha256:{hashlib.sha256(csv_path.read_bytes()).hexdigest()}"
        if fingerprint != snapshot.dataset_fingerprint:
            raise ValueError("dataset fingerprint mismatch")

        strategy = _exact_parameters(
            "strategy_parameters", snapshot.strategy_parameters, _STRATEGY_KEYS
        )
        risk = _exact_parameters("risk_parameters", snapshot.risk_parameters, _RISK_KEYS)
        cost = _exact_parameters("cost_parameters", snapshot.cost_parameters, _COST_KEYS)
        if risk["sizing_mode"] != "absolute":
            raise ValueError("only absolute sizing is supported")
        if not isinstance(strategy["allow_short"], bool):
            raise ValueError("allow_short must be boolean")

        runner = BacktestRunner(
            source=HistoricalFileSource(str(csv_path), history_policy="ignore"),
            strategy=MidBreakoutStrategy(
                lookback_bars=_integer(strategy, "lookback_bars"),
                stop_distance_pct=_number(strategy, "stop_distance_pct"),
                min_strength=_number(strategy, "min_strength"),
                allow_short=strategy["allow_short"],
            ),
            risk_engine=RiskEngine(
                RiskLimits(
                    max_position_size=_number(risk, "max_position_size"),
                    max_total_exposure=_number(risk, "max_total_exposure"),
                    risk_per_trade=_number(risk, "risk_per_trade"),
                    max_daily_drawdown=_number(risk, "max_daily_drawdown"),
                    sizing_mode="absolute",
                )
            ),
            cost_model=CostModel(
                fee_rate=_number(cost, "fee_rate"),
                spread=_number(cost, "spread"),
                slippage=_number(cost, "slippage"),
            ),
            initial_equity=_number(risk, "initial_equity"),
        )
        return _SnapshotBoundBacktestExecution(runner, str(snapshot.experiment_id))
