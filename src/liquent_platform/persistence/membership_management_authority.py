"""Persistent fail-closed workspace membership-management authority lookup."""

from sqlalchemy import Engine, text

from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipManagementAuthorityUnavailable,
)

_PERMITS = text(
    "SELECT 1 FROM identity_users AS actor"
    " JOIN workspace_membership_management_authorities AS authority"
    " ON authority.user_id=actor.user_id"
    " JOIN identity_workspaces AS workspace"
    " ON workspace.workspace_id=authority.workspace_id"
    " WHERE actor.user_id=:actor AND workspace.workspace_id=:workspace"
    " AND actor.status='active' AND workspace.status='active'"
    " AND authority.status='active'"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise WorkspaceMembershipManagementAuthorityUnavailable
    return value.encode("utf-8")


class DatabaseWorkspaceMembershipManagementAuthority:
    """Resolve exact current authority without membership or permission input."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseWorkspaceMembershipManagementAuthority()"

    def permits_workspace_membership_management(
        self, principal: SessionPrincipal, workspace_id: WorkspaceId
    ) -> bool:
        try:
            with self._engine.connect() as connection:
                row = connection.execute(
                    _PERMITS,
                    {
                        "actor": _encode(principal.user_id),
                        "workspace": _encode(workspace_id),
                    },
                ).first()
            return row is not None
        except WorkspaceMembershipManagementAuthorityUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise WorkspaceMembershipManagementAuthorityUnavailable
