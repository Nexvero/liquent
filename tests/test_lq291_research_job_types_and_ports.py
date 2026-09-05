from datetime import datetime, timedelta, timezone
from inspect import signature

import pytest

from liquent_platform.application.experiment import ExperimentSnapshot, freeze_parameters
from liquent_platform.identity.access import UserId
from liquent_platform.identity.ports import (
    AuthorizedResearchJobAcceptance,
    AuthorizedResearchJobLookup,
    ResearchJobClaim,
    ResearchJobHeartbeat,
)
from liquent_platform.identity.research import (
    ExperimentId,
    JobId,
    ResearchJobAcceptanceId,
    ResearchJobClaimId,
    ResearchJobRevisionId,
    ResearchWorkerId,
    StrategyVersionId,
    WorkspaceId,
)
from liquent_platform.identity.research_job import (
    AcceptedResearchJob,
    ClaimedResearchJob,
    RenewedResearchJobLease,
    ResearchJobAcceptanceConflict,
    ResearchJobView,
    ResearchResultArtifactClass,
)
from liquent_platform.jobs.lifecycle import ResearchJobStatus


def _snapshot() -> ExperimentSnapshot:
    return ExperimentSnapshot(
        experiment_id=ExperimentId("experiment-1"),
        workspace_id=WorkspaceId("workspace-1"),
        title="research",
        dataset_ref="dataset.csv",
        dataset_fingerprint="sha256:dataset",
        strategy_version_id=StrategyVersionId("strategy-1"),
        strategy_parameters=freeze_parameters({"period": 20}),
        risk_parameters=freeze_parameters({"risk": 0.01}),
        cost_parameters=freeze_parameters({"fee": 0.001}),
    )


def test_new_identities_are_strict_opaque_and_secret_safe():
    identity_types = (
        ResearchJobAcceptanceId,
        ResearchJobRevisionId,
        ResearchWorkerId,
        ResearchJobClaimId,
    )
    for identity_type in identity_types:
        value = identity_type("stable-1")
        assert value.value == "stable-1"
        assert "stable-1" not in repr(value)
        with pytest.raises(ValueError):
            identity_type("")
        with pytest.raises(ValueError):
            identity_type(1)  # type: ignore[arg-type]


def test_ports_accept_no_session_role_permission_allow_status_or_time():
    assert list(signature(AuthorizedResearchJobAcceptance.accept_job).parameters) == [
        "self", "acceptance_id", "actor_user_id", "snapshot", "artifact_class"
    ]
    assert list(signature(ResearchJobClaim.claim_next).parameters) == [
        "self", "worker_id"
    ]
    assert list(signature(ResearchJobHeartbeat.heartbeat).parameters) == [
        "self", "job_id", "expected_revision", "worker_id", "claim_id"
    ]
    assert list(signature(AuthorizedResearchJobLookup.get_job).parameters) == [
        "self", "actor_user_id", "job_id"
    ]


def test_acceptance_is_queued_and_conflict_is_detail_free():
    now = datetime(2026, 8, 19, tzinfo=timezone.utc)
    accepted = AcceptedResearchJob(
        ResearchJobAcceptanceId("accept-1"), JobId("job-1"),
        ResearchJobRevisionId("revision-1"), UserId("user-1"), _snapshot(),
        ResearchResultArtifactClass.BACKTEST_RESULT_V1, now,
    )
    assert accepted.status is ResearchJobStatus.QUEUED
    assert ResearchJobAcceptanceConflict() == ResearchJobAcceptanceConflict()
    assert repr(ResearchJobAcceptanceConflict()) == "ResearchJobAcceptanceConflict()"
    with pytest.raises(ValueError):
        AcceptedResearchJob(
            accepted.acceptance_id, accepted.job_id, accepted.revision_id,
            accepted.actor_user_id, accepted.snapshot, accepted.artifact_class,
            now, ResearchJobStatus.RUNNING,
        )


def test_claim_binds_snapshot_workspace_and_strictly_future_lease():
    now = datetime(2026, 8, 19, tzinfo=timezone.utc)
    claimed = ClaimedResearchJob(
        JobId("job-1"), ResearchJobRevisionId("revision-2"), UserId("user-1"),
        WorkspaceId("workspace-1"), ResearchWorkerId("worker-1"),
        ResearchJobClaimId("claim-1"), _snapshot(),
        ResearchResultArtifactClass.BACKTEST_RESULT_V1, now,
        now + timedelta(seconds=30),
    )
    assert claimed.status is ResearchJobStatus.RUNNING
    with pytest.raises(ValueError):
        ClaimedResearchJob(
            claimed.job_id, claimed.revision_id, claimed.actor_user_id,
            WorkspaceId("other"), claimed.worker_id, claimed.claim_id,
            claimed.snapshot, claimed.artifact_class, now,
            now + timedelta(seconds=30),
        )


def test_lease_and_view_require_utc_and_monotonic_observation_times():
    now = datetime(2026, 8, 19, tzinfo=timezone.utc)
    lease = RenewedResearchJobLease(
        JobId("job-1"), ResearchJobRevisionId("revision-3"),
        ResearchWorkerId("worker-1"), ResearchJobClaimId("claim-1"),
        now + timedelta(seconds=30),
    )
    assert lease.lease_expires_at > now
    view = ResearchJobView(
        JobId("job-1"), ResearchJobRevisionId("revision-3"),
        WorkspaceId("workspace-1"), ResearchJobStatus.RUNNING, now, now,
    )
    assert not hasattr(view, "claim_id")
    assert not hasattr(view, "worker_id")
    assert not hasattr(view, "lease_expires_at")
    with pytest.raises(ValueError):
        ResearchJobView(
            view.job_id, view.revision_id, view.workspace_id, view.status,
            now, now - timedelta(seconds=1),
        )
