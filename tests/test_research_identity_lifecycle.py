from __future__ import annotations

import pytest

from liquent_platform.identity.research import (
    EvidenceId,
    ExperimentId,
    JobId,
    StrategyVersionId,
    WorkspaceId,
)
from liquent_platform.jobs.lifecycle import (
    TERMINAL_STATUSES,
    ResearchJobStatus,
    can_transition,
    transition,
)


def test_research_ids_remain_strings_with_distinct_semantic_types() -> None:
    assert WorkspaceId("workspace-1") == "workspace-1"
    assert StrategyVersionId("strategy-version-1") == "strategy-version-1"
    assert ExperimentId("experiment-1") == "experiment-1"
    assert JobId("job-1") == "job-1"
    assert EvidenceId("evidence-1") == "evidence-1"
    assert WorkspaceId is not ExperimentId


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ResearchJobStatus.DRAFT, ResearchJobStatus.READY),
        (ResearchJobStatus.READY, ResearchJobStatus.QUEUED),
        (ResearchJobStatus.QUEUED, ResearchJobStatus.RUNNING),
        (ResearchJobStatus.RUNNING, ResearchJobStatus.SUCCEEDED),
        (ResearchJobStatus.RUNNING, ResearchJobStatus.FAILED),
        (ResearchJobStatus.RUNNING, ResearchJobStatus.CANCELLED),
    ],
)
def test_happy_path_and_terminal_outcomes_are_allowed(
    current: ResearchJobStatus, target: ResearchJobStatus
) -> None:
    assert can_transition(current, target)
    assert transition(current, target) is target


@pytest.mark.parametrize("terminal", sorted(TERMINAL_STATUSES, key=str))
def test_terminal_statuses_cannot_transition(terminal: ResearchJobStatus) -> None:
    for target in ResearchJobStatus:
        assert not can_transition(terminal, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ResearchJobStatus.DRAFT, ResearchJobStatus.RUNNING),
        (ResearchJobStatus.READY, ResearchJobStatus.SUCCEEDED),
        (ResearchJobStatus.QUEUED, ResearchJobStatus.SUCCEEDED),
        (ResearchJobStatus.RUNNING, ResearchJobStatus.READY),
        (ResearchJobStatus.SUCCEEDED, ResearchJobStatus.RUNNING),
    ],
)
def test_invalid_transitions_fail_closed(
    current: ResearchJobStatus, target: ResearchJobStatus
) -> None:
    with pytest.raises(ValueError, match="invalid research job transition"):
        transition(current, target)
