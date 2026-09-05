"""One-time offline bootstrap of the first global OIDC-trust authority."""

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.oidc_trust import BootstrappedOidcTrustAuthority
from liquent_platform.persistence.identity_errors import (
    OidcTrustAuthorityBootstrapUnavailable,
)

_LOCK = text(
    "LOCK TABLE identity_users, oidc_trust_management_authorities"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_HAS_AUTHORITY = text(
    "SELECT EXISTS (SELECT 1 FROM oidc_trust_management_authorities)"
)
_ACTIVE_USER = text(
    "SELECT 1 FROM identity_users WHERE user_id=:user AND status='active'"
)
_INSERT = text(
    "INSERT INTO oidc_trust_management_authorities (user_id,status)"
    " VALUES (:user,'active')"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise OidcTrustAuthorityBootstrapUnavailable
    return value.encode("utf-8")


class DatabaseInitialOidcTrustAuthorityBootstrap:
    """Grant the first global authority once, under database serialization."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def __repr__(self) -> str:
        return "DatabaseInitialOidcTrustAuthorityBootstrap()"

    def bootstrap(
        self, user_id: UserId
    ) -> BootstrappedOidcTrustAuthority | None:
        try:
            user = _encode(user_id)
            with self._engine.begin() as transaction:
                return self._bootstrap(transaction, user, user_id)
        except OidcTrustAuthorityBootstrapUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise OidcTrustAuthorityBootstrapUnavailable

    @staticmethod
    def _bootstrap(
        transaction: Connection, user: bytes, user_id: UserId
    ) -> BootstrappedOidcTrustAuthority | None:
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise OidcTrustAuthorityBootstrapUnavailable
        if transaction.scalar(_HAS_AUTHORITY):
            return None
        if transaction.execute(_ACTIVE_USER, {"user": user}).first() is None:
            return None
        transaction.execute(_INSERT, {"user": user})
        return BootstrappedOidcTrustAuthority(UserId(str(user_id)))
