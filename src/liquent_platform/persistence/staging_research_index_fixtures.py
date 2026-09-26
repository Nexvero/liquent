"""Read-only resolution of pre-provisioned staging Research-index fixtures."""

from sqlalchemy import Engine, text

from liquent_platform.application.staging_research_index_fixture_control import (
    StagingResearchIndexFixtureId,
)
from liquent_platform.application.staging_research_index_fixture_controller import (
    ResolvedStagingResearchIndexFixture,
    StagingResearchIndexFixtureControlUnavailable,
)
from liquent_platform.identity.access import MembershipStatus, Permission, UserId
from liquent_platform.identity.membership_management import WorkspaceMembershipRevisionId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal


_SELECT = text(
    "SELECT f.actor_user_id,f.target_user_id,f.workspace_id,"
    " f.active_revision_id,p.permission"
    " FROM staging_research_index_fixtures f"
    " JOIN identity_users a ON a.user_id=f.actor_user_id AND a.status='active'"
    " JOIN identity_users t ON t.user_id=f.target_user_id AND t.status='active'"
    " JOIN identity_workspaces w"
    " ON w.workspace_id=f.workspace_id AND w.status='active'"
    " JOIN workspace_membership_management_authorities ma"
    " ON ma.user_id=f.actor_user_id AND ma.workspace_id=f.workspace_id"
    " AND ma.status='active'"
    " JOIN workspace_membership_revisions r"
    " ON r.revision_id=f.active_revision_id"
    " AND r.user_id=f.target_user_id AND r.workspace_id=f.workspace_id"
    " AND r.status='active'"
    " JOIN workspace_membership_revision_permissions p"
    " ON p.revision_id=r.revision_id"
    " WHERE f.fixture_id=:fixture ORDER BY p.permission"
)


def _decode(value: object) -> str:
    if type(value) is not bytes:
        raise StagingResearchIndexFixtureControlUnavailable
    try:
        decoded = value.decode("utf-8")
    except UnicodeError:
        raise StagingResearchIndexFixtureControlUnavailable from None
    if not decoded:
        raise StagingResearchIndexFixtureControlUnavailable
    return decoded


class DatabaseStagingResearchIndexFixtures:
    """Resolve one opaque fixture from current authoritative facts."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseStagingResearchIndexFixtures()"

    def resolve(self, fixture_id: StagingResearchIndexFixtureId):
        try:
            if type(fixture_id) is not StagingResearchIndexFixtureId:
                raise StagingResearchIndexFixtureControlUnavailable
            with self._engine.connect() as connection:
                rows = connection.execute(
                    _SELECT, {"fixture": fixture_id.value.encode("utf-8")}
                ).all()
            if not rows:
                return None
            first = rows[0]
            binding = tuple(first[index] for index in range(4))
            if any(tuple(row[index] for index in range(4)) != binding for row in rows):
                raise StagingResearchIndexFixtureControlUnavailable
            permissions = frozenset(Permission(row.permission) for row in rows)
            return ResolvedStagingResearchIndexFixture(
                fixture_id=fixture_id,
                actor=SessionPrincipal(UserId(_decode(first.actor_user_id))),
                target_user_id=UserId(_decode(first.target_user_id)),
                workspace_id=WorkspaceId(_decode(first.workspace_id)),
                active_revision=WorkspaceMembershipRevisionId(
                    _decode(first.active_revision_id)
                ),
                active_status=MembershipStatus.ACTIVE,
                active_permissions=permissions,
            )
        except StagingResearchIndexFixtureControlUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise StagingResearchIndexFixtureControlUnavailable from None
