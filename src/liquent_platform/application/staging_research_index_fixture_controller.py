"""Controller adapting opaque fixtures to authorized membership changes."""

from dataclasses import dataclass, field
from typing import Protocol

from liquent_platform.application.staging_research_index_fixture_control import (
    RestoredStagingResearchIndexFixture,
    RevokedStagingResearchIndexFixture,
    StagingResearchIndexFixtureId,
    StagingResearchIndexFixtureRevision,
)
from liquent_platform.identity.access import MembershipStatus, Permission, UserId
from liquent_platform.identity.membership_management import (
    AuthorizedWorkspaceMembershipChange,
    WorkspaceMembershipChangeId,
    WorkspaceMembershipRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal


class StagingResearchIndexFixtureControlUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_fixture_control_unavailable")


@dataclass(frozen=True, slots=True)
class ResolvedStagingResearchIndexFixture:
    fixture_id: StagingResearchIndexFixtureId = field(repr=False)
    actor: SessionPrincipal = field(repr=False)
    target_user_id: UserId = field(repr=False)
    workspace_id: WorkspaceId = field(repr=False)
    active_revision: WorkspaceMembershipRevisionId = field(repr=False)
    active_status: MembershipStatus
    active_permissions: frozenset[Permission] = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.fixture_id) is not StagingResearchIndexFixtureId
            or type(self.actor) is not SessionPrincipal
            or not self.target_user_id
            or not self.workspace_id
            or type(self.active_revision) is not WorkspaceMembershipRevisionId
            or self.active_status is not MembershipStatus.ACTIVE
            or type(self.active_permissions) is not frozenset
            or not self.active_permissions
            or any(type(item) is not Permission for item in self.active_permissions)
        ):
            raise ValueError("resolved fixture is invalid")


class StagingResearchIndexFixtureResolver(Protocol):
    def resolve(
        self, fixture_id: StagingResearchIndexFixtureId
    ) -> ResolvedStagingResearchIndexFixture | None: ...


class StagingResearchIndexMembershipChanger(Protocol):
    def change_membership(
        self, change_id, principal, target_user_id, workspace_id,
        expected_revision, status, permissions,
    ) -> AuthorizedWorkspaceMembershipChange | None: ...


class StagingResearchIndexFixtureChangeIds(Protocol):
    def new_change_id(self) -> WorkspaceMembershipChangeId: ...


class AuthorizedMembershipStagingResearchIndexFixtureController:
    __slots__ = ("_changes", "_ids", "_resolver")

    def __init__(self, resolver, changes, change_ids) -> None:
        self._resolver = resolver
        self._changes = changes
        self._ids = change_ids

    def __repr__(self) -> str:
        return "AuthorizedMembershipStagingResearchIndexFixtureController()"

    def revoke(self, fixture_id, expected_active_revision):
        try:
            resolved = self._resolver.resolve(fixture_id)
            if (
                type(resolved) is not ResolvedStagingResearchIndexFixture
                or type(expected_active_revision) is not StagingResearchIndexFixtureRevision
                or resolved.active_revision.value != expected_active_revision.value
            ):
                raise StagingResearchIndexFixtureControlUnavailable
            changed = self._changes.change_membership(
                self._ids.new_change_id(), resolved.actor, resolved.target_user_id,
                resolved.workspace_id, resolved.active_revision,
                MembershipStatus.ACTIVE, frozenset(),
            )
            if type(changed) is not AuthorizedWorkspaceMembershipChange:
                raise StagingResearchIndexFixtureControlUnavailable
            return RevokedStagingResearchIndexFixture(
                fixture_id, expected_active_revision,
                StagingResearchIndexFixtureRevision(changed.revision_id.value),
            )
        except StagingResearchIndexFixtureControlUnavailable:
            raise
        except Exception:
            raise StagingResearchIndexFixtureControlUnavailable from None

    def restore(self, revoked):
        try:
            if type(revoked) is not RevokedStagingResearchIndexFixture:
                raise StagingResearchIndexFixtureControlUnavailable
            resolved = self._resolver.resolve(revoked.fixture_id)
            if (
                type(resolved) is not ResolvedStagingResearchIndexFixture
                or resolved.active_revision.value != revoked.active_revision.value
            ):
                raise StagingResearchIndexFixtureControlUnavailable
            changed = self._changes.change_membership(
                self._ids.new_change_id(), resolved.actor, resolved.target_user_id,
                resolved.workspace_id,
                WorkspaceMembershipRevisionId(revoked.revoked_revision.value),
                resolved.active_status, resolved.active_permissions,
            )
            if type(changed) is not AuthorizedWorkspaceMembershipChange:
                raise StagingResearchIndexFixtureControlUnavailable
            return RestoredStagingResearchIndexFixture(
                revoked.fixture_id, revoked.revoked_revision,
                StagingResearchIndexFixtureRevision(changed.revision_id.value),
            )
        except StagingResearchIndexFixtureControlUnavailable:
            raise
        except Exception:
            raise StagingResearchIndexFixtureControlUnavailable from None
