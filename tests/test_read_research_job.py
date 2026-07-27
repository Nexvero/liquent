import pytest

from liquent_platform.application.authorization_errors import (
    ResearchAuthorizationDenied,
)
from liquent_platform.application.experiment import ExperimentSnapshot, freeze_parameters
from liquent_platform.application.read_research_job import get_authorized_research_job
from liquent_platform.identity.access import (
    MembershipStatus,
    Permission,
    UserId,
    WorkspaceMembership,
)
from liquent_platform.identity.research import (
    ExperimentId,
    JobId,
    StrategyVersionId,
    WorkspaceId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.jobs.in_memory import InMemoryResearchJob, InMemoryResearchJobs


class StubMembershipLookup:
    def __init__(self, membership: WorkspaceMembership | None) -> None:
        self.membership = membership
        self.requested_workspace: WorkspaceId | None = None

    def get_membership(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> WorkspaceMembership | None:
        self.requested_workspace = workspace_id
        return self.membership


def _job() -> InMemoryResearchJob:
    snapshot = ExperimentSnapshot(
        experiment_id=ExperimentId("experiment-1"),
        workspace_id=WorkspaceId("workspace-stored"),
        title="Workspace-bound job",
        dataset_ref="synthetic/no-signal",
        dataset_fingerprint="sha256:dataset-1",
        strategy_version_id=StrategyVersionId("strategy-version-1"),
        strategy_parameters=freeze_parameters({}),
        risk_parameters=freeze_parameters({}),
        cost_parameters=freeze_parameters({}),
    )
    return InMemoryResearchJob(JobId("job-1"), snapshot)


def _principal() -> SessionPrincipal:
    return SessionPrincipal(UserId("user-1"))


def _membership(*, allowed: bool = True) -> WorkspaceMembership:
    return WorkspaceMembership(
        user_id=UserId("user-1"),
        workspace_id=WorkspaceId("workspace-stored"),
        status=MembershipStatus.ACTIVE,
        permissions=(
            frozenset({Permission.RESEARCH_READ}) if allowed else frozenset()
        ),
    )


def test_read_uses_workspace_stored_on_job() -> None:
    jobs = InMemoryResearchJobs()
    job = _job()
    jobs.add(job)
    memberships = StubMembershipLookup(_membership())

    result = get_authorized_research_job(jobs, memberships, _principal(), job.job_id)

    assert result is job
    assert memberships.requested_workspace == WorkspaceId("workspace-stored")


def test_read_denial_uses_neutral_authorization_error() -> None:
    jobs = InMemoryResearchJobs()
    job = _job()
    jobs.add(job)

    with pytest.raises(ResearchAuthorizationDenied, match="permission_denied"):
        get_authorized_research_job(
            jobs,
            StubMembershipLookup(_membership(allowed=False)),
            _principal(),
            job.job_id,
        )


def test_unknown_job_stays_unknown_without_membership_lookup() -> None:
    memberships = StubMembershipLookup(_membership())

    with pytest.raises(KeyError, match="research job not found"):
        get_authorized_research_job(
            InMemoryResearchJobs(),
            memberships,
            _principal(),
            JobId("missing"),
        )

    assert memberships.requested_workspace is None
