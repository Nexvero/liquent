"""Persistent read-only workspace membership and research capability lookup."""

from __future__ import annotations

from sqlalchemy import Engine, text

from liquent_platform.identity.access import (
    MembershipStatus,
    Permission,
    UserId,
    WorkspaceMembership,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipStoreUnavailable,
)

_SELECT = text(
    "SELECT m.status, p.permission FROM workspace_memberships m"
    " JOIN identity_users u ON u.user_id=m.user_id AND u.status='active'"
    " JOIN identity_workspaces w"
    " ON w.workspace_id=m.workspace_id AND w.status='active'"
    " LEFT JOIN workspace_membership_permissions p"
    " ON p.user_id=m.user_id AND p.workspace_id=m.workspace_id"
    " WHERE m.user_id=:user AND m.workspace_id=:workspace"
    " ORDER BY p.permission"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise WorkspaceMembershipStoreUnavailable
    return value.encode("utf-8")


class DatabaseWorkspaceMemberships:
    """Resolve current membership facts without mutation or caching."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseWorkspaceMemberships()"

    def get_membership(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> WorkspaceMembership | None:
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    _SELECT,
                    {
                        "user": _encode(user_id),
                        "workspace": _encode(workspace_id),
                    },
                ).all()
            if not rows:
                return None
            try:
                status = MembershipStatus(rows[0].status)
                permissions = frozenset(
                    Permission(row.permission)
                    for row in rows
                    if row.permission is not None
                )
            except (TypeError, ValueError):
                raise WorkspaceMembershipStoreUnavailable from None
            if any(row.status != rows[0].status for row in rows):
                raise WorkspaceMembershipStoreUnavailable
            return WorkspaceMembership(user_id, workspace_id, status, permissions)
        except WorkspaceMembershipStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise WorkspaceMembershipStoreUnavailable
