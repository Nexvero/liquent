from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from liquent_platform.application.experiment import ExperimentSnapshot, freeze_parameters
from liquent_platform.identity.research import ExperimentId, StrategyVersionId


def _snapshot() -> ExperimentSnapshot:
    return ExperimentSnapshot(
        experiment_id=ExperimentId("experiment-1"),
        title="Controlled no-signal run",
        dataset_ref="synthetic/no-signal",
        dataset_fingerprint="sha256:dataset-1",
        strategy_version_id=StrategyVersionId("strategy-version-1"),
        strategy_parameters=freeze_parameters({"threshold": 0.1, "lookback": 3}),
        risk_parameters=freeze_parameters({"max_exposure": 0.25}),
        cost_parameters=freeze_parameters({"fee_rate": 0.0}),
    )


def test_snapshot_is_immutable_and_parameters_are_canonical() -> None:
    snapshot = _snapshot()

    assert snapshot.strategy_parameters == (("lookback", 3), ("threshold", 0.1))
    with pytest.raises(FrozenInstanceError):
        snapshot.title = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("title", "title must not be empty"),
        ("dataset_ref", "dataset_ref must not be empty"),
        ("dataset_fingerprint", "dataset_fingerprint must not be empty"),
    ],
)
def test_snapshot_rejects_empty_required_references(field: str, message: str) -> None:
    values = _snapshot().__dict__ | {field: "  "}

    with pytest.raises(ValueError, match=message):
        ExperimentSnapshot(**values)


def test_snapshot_rejects_duplicate_or_unsorted_parameter_keys() -> None:
    values = _snapshot().__dict__ | {
        "strategy_parameters": (("threshold", 0.1), ("lookback", 3))
    }

    with pytest.raises(ValueError, match="unique, sorted keys"):
        ExperimentSnapshot(**values)
