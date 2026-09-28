from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from liquent_platform.application.experiment import ExperimentSnapshot, freeze_parameters
from liquent_platform.application.local_csv import LocalCsvMidBreakoutV0Resolver
from liquent_platform.identity.research import ExperimentId, StrategyVersionId, WorkspaceId


FIXTURES = Path(__file__).parent / "fixtures"


def _fingerprint(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _snapshot(**changes: object) -> ExperimentSnapshot:
    csv_path = FIXTURES / "ohlcv_valid.csv"
    values: dict[str, object] = {
        "experiment_id": ExperimentId("experiment-1"),
        "workspace_id": WorkspaceId("workspace-1"),
        "title": "Local CSV run",
        "dataset_ref": csv_path.name,
        "dataset_fingerprint": _fingerprint(csv_path),
        "strategy_version_id": StrategyVersionId("mid-breakout-v0"),
        "strategy_parameters": freeze_parameters(
            {
                "lookback_bars": 1,
                "stop_distance_pct": 0.05,
                "min_strength": 0.0,
                "allow_short": True,
            }
        ),
        "risk_parameters": freeze_parameters(
            {
                "initial_equity": 1_000.0,
                "max_position_size": 10.0,
                "max_total_exposure": 100.0,
                "risk_per_trade": 5.0,
                "max_daily_drawdown": 1_000.0,
                "sizing_mode": "absolute",
            }
        ),
        "cost_parameters": freeze_parameters(
            {"fee_rate": 0.0, "spread": 0.0, "slippage": 0.0}
        ),
    }
    values.update(changes)
    return ExperimentSnapshot(**values)  # type: ignore[arg-type]


def test_resolver_builds_existing_runner_for_one_supported_local_path() -> None:
    runner = LocalCsvMidBreakoutV0Resolver(FIXTURES).resolve(_snapshot())

    result = runner.run()

    assert result.experiment_id == "experiment-1"
    assert result.parameters["bars"] == 3
    assert result.parameters["strategy"] == "MidBreakoutStrategy"
    assert result.parameters["sizing_mode"] == "absolute"
    assert result.parameters["network_calls"] is False
    assert result.parameters["live_execution"] is False


def test_resolver_rejects_dataset_outside_data_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside.csv"
    outside.write_text((FIXTURES / "ohlcv_valid.csv").read_text(), encoding="utf-8")

    with pytest.raises(ValueError, match="below the configured data root"):
        LocalCsvMidBreakoutV0Resolver(FIXTURES).resolve(
            _snapshot(dataset_ref=str(outside))
        )


def test_resolver_rejects_changed_dataset_content() -> None:
    with pytest.raises(ValueError, match="dataset fingerprint mismatch"):
        LocalCsvMidBreakoutV0Resolver(FIXTURES).resolve(
            _snapshot(dataset_fingerprint="sha256:not-the-file")
        )


def test_resolver_rejects_other_strategy_or_incomplete_parameters() -> None:
    resolver = LocalCsvMidBreakoutV0Resolver(FIXTURES)

    with pytest.raises(ValueError, match="unsupported strategy version"):
        resolver.resolve(_snapshot(strategy_version_id=StrategyVersionId("v1")))
    with pytest.raises(ValueError, match="strategy_parameters must contain exactly"):
        resolver.resolve(
            _snapshot(strategy_parameters=freeze_parameters({"lookback_bars": 1}))
        )


def test_resolver_does_not_coerce_string_parameters() -> None:
    parameters = dict(_snapshot().strategy_parameters)
    parameters["allow_short"] = "false"

    with pytest.raises(ValueError, match="allow_short must be boolean"):
        LocalCsvMidBreakoutV0Resolver(FIXTURES).resolve(
            _snapshot(strategy_parameters=freeze_parameters(parameters))
        )
