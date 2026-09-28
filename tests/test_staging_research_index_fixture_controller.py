from dataclasses import replace

import pytest

from liquent_platform.application.staging_research_index_fixture_control import (
    StagingResearchIndexFixtureId,
    StagingResearchIndexFixtureRevision,
)
from liquent_platform.application.staging_research_index_fixture_controller import (
    AuthorizedMembershipStagingResearchIndexFixtureController,
    ResolvedStagingResearchIndexFixture,
    StagingResearchIndexFixtureControlUnavailable,
)
from liquent_platform.identity.access import MembershipStatus, Permission, UserId
from liquent_platform.identity.membership_management import (
    AuthorizedWorkspaceMembershipChange,
    WorkspaceMembershipChangeId,
    WorkspaceMembershipRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal


FIXTURE = StagingResearchIndexFixtureId("opaque-fixture-0001")
ACTIVE = WorkspaceMembershipRevisionId("active-revision-001")
RESOLVED = ResolvedStagingResearchIndexFixture(
    FIXTURE, SessionPrincipal(UserId("manager")), UserId("reader"),
    WorkspaceId("workspace"), ACTIVE, MembershipStatus.ACTIVE,
    frozenset({Permission.RESEARCH_READ}),
)


class Resolver:
    def __init__(self, value=RESOLVED): self.value = value
    def resolve(self, fixture_id): return self.value if fixture_id == FIXTURE else None


class Ids:
    def __init__(self): self.number = 0
    def new_change_id(self):
        self.number += 1
        return WorkspaceMembershipChangeId(f"change-{self.number}")


class Changes:
    def __init__(self): self.calls = []
    def change_membership(self, change_id, principal, target, workspace,
                          expected, status, permissions):
        self.calls.append((principal, target, workspace, expected, status, permissions))
        revision = WorkspaceMembershipRevisionId(
            f"result-revision-{len(self.calls):04d}"
        )
        return AuthorizedWorkspaceMembershipChange(
            change_id, revision, target, workspace, status, permissions
        )


def test_revoke_and_restore_use_only_resolved_target_and_snapshot() -> None:
    changes = Changes()
    controller = AuthorizedMembershipStagingResearchIndexFixtureController(
        Resolver(), changes, Ids()
    )
    revoked = controller.revoke(
        FIXTURE, StagingResearchIndexFixtureRevision(ACTIVE.value)
    )
    restored = controller.restore(revoked)
    assert changes.calls[0] == (
        RESOLVED.actor, RESOLVED.target_user_id, RESOLVED.workspace_id, ACTIVE,
        MembershipStatus.ACTIVE, frozenset(),
    )
    assert changes.calls[1][-2:] == (
        MembershipStatus.ACTIVE, RESOLVED.active_permissions
    )
    assert restored.revoked_revision == revoked.revoked_revision


def test_stale_expected_revision_fails_before_mutation() -> None:
    changes = Changes()
    controller = AuthorizedMembershipStagingResearchIndexFixtureController(
        Resolver(), changes, Ids()
    )
    with pytest.raises(StagingResearchIndexFixtureControlUnavailable):
        controller.revoke(
            FIXTURE, StagingResearchIndexFixtureRevision("stale-revision-001")
        )
    assert changes.calls == []


def test_missing_fixture_and_rejected_change_fail_closed() -> None:
    class Rejected(Changes):
        def change_membership(self, *args): return None

    for resolver, changes in ((Resolver(None), Changes()), (Resolver(), Rejected())):
        controller = AuthorizedMembershipStagingResearchIndexFixtureController(
            resolver, changes, Ids()
        )
        with pytest.raises(StagingResearchIndexFixtureControlUnavailable):
            controller.revoke(
                FIXTURE, StagingResearchIndexFixtureRevision(ACTIVE.value)
            )


def test_restore_re_resolves_fixture_and_rejects_binding_change() -> None:
    resolver = Resolver()
    controller = AuthorizedMembershipStagingResearchIndexFixtureController(
        resolver, Changes(), Ids()
    )
    revoked = controller.revoke(
        FIXTURE, StagingResearchIndexFixtureRevision(ACTIVE.value)
    )
    resolver.value = replace(
        RESOLVED, active_revision=WorkspaceMembershipRevisionId("other-active")
    )
    with pytest.raises(StagingResearchIndexFixtureControlUnavailable):
        controller.restore(revoked)


def test_controller_repr_exposes_no_fixture_or_identity() -> None:
    controller = AuthorizedMembershipStagingResearchIndexFixtureController(
        Resolver(), Changes(), Ids()
    )
    assert repr(controller) == "AuthorizedMembershipStagingResearchIndexFixtureController()"
