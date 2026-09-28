"""Semantic identities used by local and persistent research workflows."""

from dataclasses import dataclass, field
from typing import NewType


WorkspaceId = NewType("WorkspaceId", str)
StrategyVersionId = NewType("StrategyVersionId", str)
ExperimentId = NewType("ExperimentId", str)
JobId = NewType("JobId", str)
EvidenceId = NewType("EvidenceId", str)


def _require_identifier(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ResearchJobAcceptanceId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "research job acceptance id")


@dataclass(frozen=True, slots=True)
class ResearchJobRevisionId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "research job revision id")


@dataclass(frozen=True, slots=True)
class ResearchWorkerId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "research worker id")


@dataclass(frozen=True, slots=True)
class ResearchJobClaimId:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_identifier(self.value, "research job claim id")
