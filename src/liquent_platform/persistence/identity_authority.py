"""Persistent, fail-closed onboarding-management authority resolution."""

from __future__ import annotations

from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    IdentityAuthorityStoreUnavailable,
)

_PERMITS = text(
    "SELECT 1"
    " FROM identity_users AS actor"
    " JOIN workspace_onboarding_management AS authority"
    "   ON authority.user_id = actor.user_id"
    " JOIN identity_workspaces AS workspace"
    "   ON workspace.workspace_id = authority.workspace_id"
    " JOIN identity_users AS target"
    "   ON target.user_id = :target_user"
    " WHERE actor.user_id = :actor"
    "   AND workspace.workspace_id = :workspace"
    "   AND actor.status = 'active'"
    "   AND target.status = 'active'"
    "   AND workspace.status = 'active'"
    "   AND authority.status = 'active'"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise IdentityAuthorityStoreUnavailable
    return value.encode("utf-8")


class DatabaseOnboardingManagementAuthority:
    """Resolve current authority solely from persistent internal facts."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseOnboardingManagementAuthority()"

    def permits_onboarding_management(
        self,
        principal: SessionPrincipal,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
    ) -> bool:
        try:
            actor = _encode(principal.user_id)
            target = _encode(target_user_id)
            workspace = _encode(target_workspace_id)
            with self._engine.connect() as connection:
                row = connection.execute(
                    _PERMITS,
                    {"actor": actor, "target_user": target, "workspace": workspace},
                ).first()
            return row is not None
        except IdentityAuthorityStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise IdentityAuthorityStoreUnavailable
