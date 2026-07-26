"""Semantic identities used by the local research workflow."""

from typing import NewType


WorkspaceId = NewType("WorkspaceId", str)
StrategyVersionId = NewType("StrategyVersionId", str)
ExperimentId = NewType("ExperimentId", str)
JobId = NewType("JobId", str)
EvidenceId = NewType("EvidenceId", str)
