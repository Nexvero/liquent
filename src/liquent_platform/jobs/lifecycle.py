"""Explicit lifecycle for research jobs; no trading execution semantics."""

from __future__ import annotations

from enum import Enum


class ResearchJobStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INVALIDATED = "invalidated"
    DISCARDED = "discarded"


TERMINAL_STATUSES = frozenset(
    {
        ResearchJobStatus.SUCCEEDED,
        ResearchJobStatus.FAILED,
        ResearchJobStatus.CANCELLED,
        ResearchJobStatus.INVALIDATED,
        ResearchJobStatus.DISCARDED,
    }
)


_ALLOWED_TRANSITIONS = {
    ResearchJobStatus.DRAFT: frozenset(
        {ResearchJobStatus.READY, ResearchJobStatus.DISCARDED}
    ),
    ResearchJobStatus.READY: frozenset(
        {
            ResearchJobStatus.QUEUED,
            ResearchJobStatus.INVALIDATED,
            ResearchJobStatus.DISCARDED,
        }
    ),
    ResearchJobStatus.QUEUED: frozenset(
        {
            ResearchJobStatus.RUNNING,
            ResearchJobStatus.FAILED,
            ResearchJobStatus.CANCELLED,
        }
    ),
    ResearchJobStatus.RUNNING: frozenset(
        {
            ResearchJobStatus.SUCCEEDED,
            ResearchJobStatus.FAILED,
            ResearchJobStatus.CANCELLED,
        }
    ),
}


def can_transition(current: ResearchJobStatus, target: ResearchJobStatus) -> bool:
    """Return whether a research job may move directly to ``target``."""

    return target in _ALLOWED_TRANSITIONS.get(current, frozenset())


def transition(current: ResearchJobStatus, target: ResearchJobStatus) -> ResearchJobStatus:
    """Apply one valid transition or fail without changing state."""

    if not can_transition(current, target):
        raise ValueError(f"invalid research job transition: {current.value} -> {target.value}")
    return target
