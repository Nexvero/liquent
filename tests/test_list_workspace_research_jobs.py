from datetime import datetime, timezone

import pytest

from liquent_platform.application.list_workspace_research_jobs import (
    list_current_workspace_research_jobs,
)
from liquent_platform.identity.access import (
    CurrentWorkspaceContext,
    MembershipStatus,
    Permission,
    UserId,
    WorkspaceMembership,
)
from liquent_platform.identity.research import JobId, WorkspaceId
from liquent_platform.identity.research_job import ResearchJobIndexItem
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.jobs.lifecycle import ResearchJobStatus
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipStoreUnavailable,
)
from liquent_platform.persistence.research_jobs import ResearchJobStoreUnavailable

USER = UserId("index-actor")
WORKSPACE = WorkspaceId("current-workspace")
PRINCIPAL = SessionPrincipal(USER)
CONTEXT = CurrentWorkspaceContext(USER, WORKSPACE)
NOW = datetime(2026, 9, 15, tzinfo=timezone.utc)
ITEMS = (
    ResearchJobIndexItem(JobId("job-1"), ResearchJobStatus.QUEUED, NOW, NOW),
)


class Contexts:
    def __init__(self, context=CONTEXT, error=None):
        self.context = context
        self.error = error

    def resolve_current_workspace(self, user_id):
        if self.error is not None:
            raise self.error
        assert user_id == USER
        return self.context


class Memberships:
    def __init__(self, allowed=True, error=None):
        self.allowed = allowed
        self.error = error

    def get_membership(self, user_id, workspace_id):
        if self.error is not None:
            raise self.error
        assert (user_id, workspace_id) == (USER, WORKSPACE)
        permissions = (
            frozenset({Permission.RESEARCH_READ}) if self.allowed else frozenset()
        )
        return WorkspaceMembership(
            USER,
            WORKSPACE,
            MembershipStatus.ACTIVE,
            permissions,
        )


class Jobs:
    def __init__(self, result=ITEMS, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def list_jobs(self, actor_user_id, workspace_id):
        self.calls.append((actor_user_id, workspace_id))
        if self.error is not None:
            raise self.error
        return self.result


def test_authorized_index_binds_actor_and_resolved_workspace() -> None:
    jobs = Jobs()

    result = list_current_workspace_research_jobs(
        Contexts(), Memberships(), jobs, PRINCIPAL
    )

    assert result == ITEMS
    assert jobs.calls == [(USER, WORKSPACE)]


def test_authorized_empty_is_distinct_from_neutral_denial() -> None:
    empty_jobs = Jobs(result=())
    denied_jobs = Jobs()

    assert list_current_workspace_research_jobs(
        Contexts(), Memberships(), empty_jobs, PRINCIPAL
    ) == ()
    assert list_current_workspace_research_jobs(
        Contexts(), Memberships(allowed=False), denied_jobs, PRINCIPAL
    ) is None
    assert denied_jobs.calls == []


def test_absent_context_does_not_query_membership_or_jobs() -> None:
    memberships = Memberships(error=AssertionError("membership queried"))
    jobs = Jobs(error=AssertionError("jobs queried"))

    assert list_current_workspace_research_jobs(
        Contexts(context=None), memberships, jobs, PRINCIPAL
    ) is None
    assert jobs.calls == []


def test_mismatched_context_fails_closed_without_index_lookup() -> None:
    jobs = Jobs()
    mismatched = CurrentWorkspaceContext(UserId("other-actor"), WORKSPACE)

    assert list_current_workspace_research_jobs(
        Contexts(mismatched), Memberships(), jobs, PRINCIPAL
    ) is None
    assert jobs.calls == []


@pytest.mark.parametrize(
    "contexts,memberships,jobs,error_type",
    [
        (
            Contexts(error=WorkspaceMembershipStoreUnavailable()),
            Memberships(),
            Jobs(),
            WorkspaceMembershipStoreUnavailable,
        ),
        (
            Contexts(),
            Memberships(error=WorkspaceMembershipStoreUnavailable()),
            Jobs(),
            WorkspaceMembershipStoreUnavailable,
        ),
        (
            Contexts(),
            Memberships(),
            Jobs(error=ResearchJobStoreUnavailable()),
            ResearchJobStoreUnavailable,
        ),
    ],
)
def test_technical_unavailability_is_not_translated(
    contexts, memberships, jobs, error_type
) -> None:
    with pytest.raises(error_type):
        list_current_workspace_research_jobs(
            contexts, memberships, jobs, PRINCIPAL
        )
