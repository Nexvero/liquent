"""Immutable input snapshot for one validated research experiment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, TypeAlias

from liquent_platform.identity.research import ExperimentId, StrategyVersionId


ParameterValue: TypeAlias = str | int | float | bool
ParameterSet: TypeAlias = tuple[tuple[str, ParameterValue], ...]


def freeze_parameters(parameters: Mapping[str, ParameterValue]) -> ParameterSet:
    """Return a stable, immutable parameter representation."""

    return tuple(sorted(parameters.items()))


@dataclass(frozen=True)
class ExperimentSnapshot:
    """Validated references and effective inputs used by one research run."""

    experiment_id: ExperimentId
    title: str
    dataset_ref: str
    dataset_fingerprint: str
    strategy_version_id: StrategyVersionId
    strategy_parameters: ParameterSet
    risk_parameters: ParameterSet
    cost_parameters: ParameterSet

    def __post_init__(self) -> None:
        for name, value in (
            ("experiment_id", self.experiment_id),
            ("title", self.title),
            ("dataset_ref", self.dataset_ref),
            ("dataset_fingerprint", self.dataset_fingerprint),
            ("strategy_version_id", self.strategy_version_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")

        for name, parameters in (
            ("strategy_parameters", self.strategy_parameters),
            ("risk_parameters", self.risk_parameters),
            ("cost_parameters", self.cost_parameters),
        ):
            keys = tuple(key for key, _ in parameters)
            if keys != tuple(sorted(set(keys))):
                raise ValueError(f"{name} must have unique, sorted keys")
