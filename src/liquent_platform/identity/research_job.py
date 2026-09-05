"""Closed values crossing the persistent research-job ports."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from liquent.backtesting.reporting import BacktestExperimentSummary
from liquent_platform.application.ports import ArtifactReference
from liquent_platform.application.experiment import ExperimentSnapshot
from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import (
    JobId,
    ResearchJobAcceptanceId,
    ResearchJobClaimId,
    ResearchJobRevisionId,
    ResearchWorkerId,
    WorkspaceId,
)
from liquent_platform.jobs.lifecycle import ResearchJobStatus


def _require_utc(value: object, name: str) -> None:
    if type(value) is not datetime or value.tzinfo is None:
        raise ValueError(f"{name} must be an aware UTC datetime")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{name} must be an aware UTC datetime")


class ResearchResultArtifactClass(str, Enum):
    """Controlled result shape accepted by the first persistent queue."""

    BACKTEST_RESULT_V1 = "backtest_result_v1"


class ResearchJobFailureCode(str, Enum):
    EXECUTION_FAILED = "execution_failed"


@dataclass(frozen=True, slots=True)
class CompletedResearchJob:
    job_id: JobId = field(repr=False)
    revision_id: ResearchJobRevisionId = field(repr=False)
    status: ResearchJobStatus
    completed_at: datetime
    summary: BacktestExperimentSummary | None = field(default=None, repr=False)
    artifact: ArtifactReference | None = field(default=None, repr=False)
    failure_code: ResearchJobFailureCode | None = None

    def __post_init__(self) -> None:
        _require_utc(self.completed_at, "research job completion time")
        success = self.status is ResearchJobStatus.SUCCEEDED
        failure = self.status is ResearchJobStatus.FAILED
        if not (success or failure):
            raise ValueError("completed research job must be succeeded or failed")
        if success != (self.summary is not None and self.artifact is not None):
            raise ValueError("successful research job requires result and artifact")
        if success == (self.failure_code is not None):
            raise ValueError("research job failure code does not match status")


@dataclass(frozen=True, slots=True)
class ResearchJobAcceptanceConflict:
    """Detail-free divergent reuse of an existing acceptance identity."""


@dataclass(frozen=True, slots=True)
class AcceptedResearchJob:
    acceptance_id: ResearchJobAcceptanceId = field(repr=False)
    job_id: JobId = field(repr=False)
    revision_id: ResearchJobRevisionId = field(repr=False)
    actor_user_id: UserId = field(repr=False)
    snapshot: ExperimentSnapshot = field(repr=False)
    artifact_class: ResearchResultArtifactClass
    accepted_at: datetime
    status: ResearchJobStatus = ResearchJobStatus.QUEUED

    def __post_init__(self) -> None:
        _require_utc(self.accepted_at, "research job acceptance time")
        if self.status is not ResearchJobStatus.QUEUED:
            raise ValueError("accepted research job must be queued")


@dataclass(frozen=True, slots=True)
class ClaimedResearchJob:
    job_id: JobId = field(repr=False)
    revision_id: ResearchJobRevisionId = field(repr=False)
    actor_user_id: UserId = field(repr=False)
    workspace_id: WorkspaceId = field(repr=False)
    worker_id: ResearchWorkerId = field(repr=False)
    claim_id: ResearchJobClaimId = field(repr=False)
    snapshot: ExperimentSnapshot = field(repr=False)
    artifact_class: ResearchResultArtifactClass
    claimed_at: datetime
    lease_expires_at: datetime
    status: ResearchJobStatus = ResearchJobStatus.RUNNING

    def __post_init__(self) -> None:
        _require_utc(self.claimed_at, "research job claim time")
        _require_utc(self.lease_expires_at, "research job lease expiry")
        if self.lease_expires_at <= self.claimed_at:
            raise ValueError("research job lease expiry must follow claim time")
        if self.status is not ResearchJobStatus.RUNNING:
            raise ValueError("claimed research job must be running")
        if self.snapshot.workspace_id != self.workspace_id:
            raise ValueError("claimed research job workspace must match snapshot")


@dataclass(frozen=True, slots=True)
class RenewedResearchJobLease:
    job_id: JobId = field(repr=False)
    revision_id: ResearchJobRevisionId = field(repr=False)
    worker_id: ResearchWorkerId = field(repr=False)
    claim_id: ResearchJobClaimId = field(repr=False)
    lease_expires_at: datetime

    def __post_init__(self) -> None:
        _require_utc(self.lease_expires_at, "research job lease expiry")


@dataclass(frozen=True, slots=True)
class ResearchJobView:
    job_id: JobId = field(repr=False)
    revision_id: ResearchJobRevisionId = field(repr=False)
    workspace_id: WorkspaceId = field(repr=False)
    status: ResearchJobStatus
    accepted_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_utc(self.accepted_at, "research job acceptance time")
        _require_utc(self.updated_at, "research job update time")
        if self.updated_at < self.accepted_at:
            raise ValueError("research job update time must not precede acceptance")
