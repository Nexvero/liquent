"""Persistent fail-closed system-wide OIDC-trust authority resolution."""

from sqlalchemy import Engine, text

from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    OidcTrustAuthorityStoreUnavailable,
)

_PERMITS = text(
    "SELECT 1 FROM identity_users AS actor"
    " JOIN oidc_trust_management_authorities AS authority"
    " ON authority.user_id=actor.user_id"
    " WHERE actor.user_id=:actor"
    " AND actor.status='active' AND authority.status='active'"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise OidcTrustAuthorityStoreUnavailable
    return value.encode("utf-8")


class DatabaseOidcTrustManagementAuthority:
    """Resolve current global authority solely from persistent internal facts."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseOidcTrustManagementAuthority()"

    def permits_oidc_trust_management(self, principal: SessionPrincipal) -> bool:
        try:
            with self._engine.connect() as connection:
                row = connection.execute(
                    _PERMITS, {"actor": _encode(principal.user_id)}
                ).first()
            return row is not None
        except OidcTrustAuthorityStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise OidcTrustAuthorityStoreUnavailable
