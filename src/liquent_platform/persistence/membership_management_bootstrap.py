"""One-time per-workspace bootstrap of initial membership management."""

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.membership_management import (
    BootstrappedWorkspaceMembershipManagementAuthority,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipManagementBootstrapUnavailable,
)

_LOCK = text(
    "LOCK TABLE identity_users, identity_workspaces,"
    " workspace_membership_management_authorities"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_HAS_AUTHORITY = text(
    "SELECT EXISTS (SELECT 1 FROM workspace_membership_management_authorities"
    " WHERE workspace_id=:workspace)"
)
_ACTIVE_FOUNDATION = text(
    "SELECT 1 FROM identity_users AS users CROSS JOIN identity_workspaces AS workspaces"
    " WHERE users.user_id=:user AND users.status='active'"
    " AND workspaces.workspace_id=:workspace AND workspaces.status='active'"
)
_INSERT = text(
    "INSERT INTO workspace_membership_management_authorities"
    " (user_id,workspace_id,status) VALUES (:user,:workspace,'active')"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise WorkspaceMembershipManagementBootstrapUnavailable
    return value.encode("utf-8")


class DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap:
    """Grant exactly the first authority fact in one workspace scope."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap()"

    def bootstrap(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> BootstrappedWorkspaceMembershipManagementAuthority | None:
        try:
            user = _encode(user_id)
            workspace = _encode(workspace_id)
            with self._engine.begin() as transaction:
                return self._bootstrap(
                    transaction, user, workspace, user_id, workspace_id
                )
        except WorkspaceMembershipManagementBootstrapUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise WorkspaceMembershipManagementBootstrapUnavailable

    @staticmethod
    def _bootstrap(
        transaction: Connection,
        user: bytes,
        workspace: bytes,
        user_id: UserId,
        workspace_id: WorkspaceId,
    ) -> BootstrappedWorkspaceMembershipManagementAuthority | None:
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise WorkspaceMembershipManagementBootstrapUnavailable
        parameters = {"user": user, "workspace": workspace}
        if transaction.scalar(_HAS_AUTHORITY, parameters):
            return None
        if transaction.execute(_ACTIVE_FOUNDATION, parameters).first() is None:
            return None
        transaction.execute(_INSERT, parameters)
        return BootstrappedWorkspaceMembershipManagementAuthority(
            UserId(str(user_id)), WorkspaceId(str(workspace_id))
        )
