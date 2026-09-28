"""Persistent resolution of one unambiguous current workspace context."""

from __future__ import annotations

from sqlalchemy import Engine, text

from liquent_platform.identity.access import CurrentWorkspaceContext, UserId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipStoreUnavailable,
)

_SELECT = text(
    "SELECT m.workspace_id FROM workspace_memberships m"
    " JOIN identity_users u ON u.user_id=m.user_id AND u.status='active'"
    " JOIN identity_workspaces w"
    " ON w.workspace_id=m.workspace_id AND w.status='active'"
    " WHERE m.user_id=:user AND m.status='active'"
    " ORDER BY m.workspace_id"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise WorkspaceMembershipStoreUnavailable
    return value.encode("utf-8")


def _decode(value: object) -> str:
    if type(value) is not bytes:
        raise WorkspaceMembershipStoreUnavailable
    try:
        decoded = value.decode("utf-8")
    except UnicodeDecodeError:
        raise WorkspaceMembershipStoreUnavailable from None
    if not decoded:
        raise WorkspaceMembershipStoreUnavailable
    return decoded


class DatabaseCurrentWorkspaceContexts:
    """Read current active facts on every resolution without choosing a row."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseCurrentWorkspaceContexts()"

    def resolve_current_workspace(
        self, user_id: UserId
    ) -> CurrentWorkspaceContext | None:
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(_SELECT, {"user": _encode(user_id)}).all()
            if len(rows) != 1:
                return None
            return CurrentWorkspaceContext(
                user_id=user_id,
                workspace_id=WorkspaceId(_decode(rows[0].workspace_id)),
            )
        except WorkspaceMembershipStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise WorkspaceMembershipStoreUnavailable
