"""Persistent fail-closed global lifecycle authority resolution."""

from sqlalchemy import Engine, text

from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    LifecycleAuthorityStoreUnavailable,
)

_USER = text(
    "SELECT 1 FROM identity_users AS actor"
    " JOIN user_lifecycle_management_authorities AS authority"
    " ON authority.user_id=actor.user_id"
    " WHERE actor.user_id=:actor"
    " AND actor.status='active' AND authority.status='active'"
)
_WORKSPACE = text(
    "SELECT 1 FROM identity_users AS actor"
    " JOIN workspace_lifecycle_management_authorities AS authority"
    " ON authority.user_id=actor.user_id"
    " WHERE actor.user_id=:actor"
    " AND actor.status='active' AND authority.status='active'"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise LifecycleAuthorityStoreUnavailable
    return value.encode("utf-8")


class _DatabaseLifecycleAuthority:
    __slots__ = ("_engine",)
    query = _USER

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _permits(self, principal: SessionPrincipal) -> bool:
        try:
            with self._engine.connect() as connection:
                row = connection.execute(
                    self.query, {"actor": _encode(principal.user_id)}
                ).first()
            return row is not None
        except LifecycleAuthorityStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise LifecycleAuthorityStoreUnavailable


class DatabaseUserLifecycleManagementAuthority(_DatabaseLifecycleAuthority):
    """Resolve only the dedicated current global user-lifecycle authority."""

    def __repr__(self) -> str:
        return "DatabaseUserLifecycleManagementAuthority()"

    def permits_user_lifecycle_management(self, principal: SessionPrincipal) -> bool:
        return self._permits(principal)


class DatabaseWorkspaceLifecycleManagementAuthority(_DatabaseLifecycleAuthority):
    """Resolve only the dedicated current global workspace-lifecycle authority."""

    query = _WORKSPACE

    def __repr__(self) -> str:
        return "DatabaseWorkspaceLifecycleManagementAuthority()"

    def permits_workspace_lifecycle_management(
        self, principal: SessionPrincipal
    ) -> bool:
        return self._permits(principal)
