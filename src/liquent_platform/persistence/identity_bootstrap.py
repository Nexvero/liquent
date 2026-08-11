"""Atomic persistence for the first internal identity authority."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import Connection, Engine, Row, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    ProvisioningRequestId,
)
from liquent_platform.identity.bootstrap import BootstrappedIdentityAuthority
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.identity_errors import (
    IdentityAuthorityBootstrapUnavailable,
)
from liquent_platform.persistence.identity_provisioning import _lifetime_microseconds

_SINGLETON = 1
_LOCK_TABLE = text(
    "LOCK TABLE identity_authority_bootstrap_decisions IN SHARE ROW EXCLUSIVE MODE"
)
_LOAD_DECISION = text(
    "SELECT d.singleton_key, a.admission_id, a.provisioning_request,"
    " a.target_user_id, a.target_workspace_id, u.user_id AS foundation_user_id,"
    " w.workspace_id AS foundation_workspace_id,"
    " x.user_id AS authority_user_id, x.workspace_id AS authority_workspace_id"
    " FROM identity_authority_bootstrap_decisions d"
    " LEFT JOIN identity_admissions a ON a.admission_id = d.admission_id"
    " LEFT JOIN internal_users u ON u.user_id = a.target_user_id"
    " LEFT JOIN workspaces w ON w.workspace_id = a.target_workspace_id"
    " LEFT JOIN workspace_onboarding_authorities x"
    " ON x.user_id = a.target_user_id AND x.workspace_id = a.target_workspace_id"
    " WHERE d.singleton_key = :singleton"
)
_HAS_FOUNDATION = text(
    "SELECT CASE WHEN"
    " EXISTS (SELECT 1 FROM internal_users) OR"
    " EXISTS (SELECT 1 FROM workspaces) OR"
    " EXISTS (SELECT 1 FROM workspace_onboarding_authorities)"
    " THEN 1 ELSE 0 END"
)
_INSERT_USER = text(
    "INSERT INTO internal_users (user_id, status) VALUES (:user, 'active')"
)
_INSERT_WORKSPACE = text(
    "INSERT INTO workspaces (workspace_id, status) VALUES (:workspace, 'active')"
)
_INSERT_AUTHORITY = text(
    "INSERT INTO workspace_onboarding_authorities"
    " (user_id, workspace_id, status) VALUES (:user, :workspace, 'active')"
)
_INSERT_ADMISSION = text(
    "INSERT INTO identity_admissions"
    " (admission_id, provisioning_request, target_user_id, target_workspace_id,"
    " lifetime_microseconds, expires_at, consumed_at, bound_issuer, bound_subject)"
    " VALUES (:admission, :request, :user, :workspace, :lifetime, :expires_at,"
    " NULL, NULL, NULL)"
)
_INSERT_DECISION = text(
    "INSERT INTO identity_authority_bootstrap_decisions"
    " (singleton_key, admission_id) VALUES (:singleton, :admission)"
)


def _identifier(value: object) -> bytes:
    if type(value) is not str or not value:
        raise IdentityAuthorityBootstrapUnavailable
    return value.encode("utf-8")


def _decoded(value: object) -> str:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise IdentityAuthorityBootstrapUnavailable
    try:
        decoded = bytes(value).decode("utf-8")
    except UnicodeDecodeError:
        raise IdentityAuthorityBootstrapUnavailable from None
    if not decoded:
        raise IdentityAuthorityBootstrapUnavailable
    return decoded


class DatabaseIdentityAuthorityBootstrapStore:
    """Create the initial user, workspace, authority, and admission once."""

    __slots__ = (
        "_admission_lifetime",
        "_engine",
        "_generate_admission_id",
        "_generate_request_id",
        "_generate_user_id",
        "_generate_workspace_id",
        "_lifetime_microseconds",
        "_now",
    )

    def __init__(
        self,
        engine: Engine,
        *,
        generate_user_id: Callable[[], UserId],
        generate_workspace_id: Callable[[], WorkspaceId],
        generate_request_id: Callable[[], ProvisioningRequestId],
        generate_admission_id: Callable[[], IdentityAdmissionId],
        now: Callable[[], datetime],
        admission_lifetime: timedelta,
    ) -> None:
        try:
            duration = _lifetime_microseconds(admission_lifetime)
        except Exception:
            raise ValueError("invalid admission lifetime") from None
        self._engine = engine
        self._generate_user_id = generate_user_id
        self._generate_workspace_id = generate_workspace_id
        self._generate_request_id = generate_request_id
        self._generate_admission_id = generate_admission_id
        self._now = now
        self._admission_lifetime = admission_lifetime
        self._lifetime_microseconds = duration

    def __repr__(self) -> str:
        return "DatabaseIdentityAuthorityBootstrapStore()"

    def bootstrap_initial_identity(self) -> BootstrappedIdentityAuthority | None:
        try:
            return self._bootstrap()
        except IdentityAuthorityBootstrapUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise IdentityAuthorityBootstrapUnavailable()

    def _bootstrap(self) -> BootstrappedIdentityAuthority | None:
        with self._engine.begin() as transaction:
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK_TABLE)
            existing = transaction.execute(
                _LOAD_DECISION, {"singleton": _SINGLETON}
            ).first()
            if existing is not None:
                return self._resolve(existing)
            if transaction.scalar(_HAS_FOUNDATION) == 1:
                return None
            return self._create(transaction)

    def _create(self, transaction: Connection) -> BootstrappedIdentityAuthority:
        generated_user = self._generate_user_id()
        generated_workspace = self._generate_workspace_id()
        generated_request = self._generate_request_id()
        generated_admission = self._generate_admission_id()
        if type(generated_request) is not ProvisioningRequestId:
            raise IdentityAuthorityBootstrapUnavailable
        if type(generated_admission) is not IdentityAdmissionId:
            raise IdentityAuthorityBootstrapUnavailable
        user = _identifier(generated_user)
        workspace = _identifier(generated_workspace)
        request = _identifier(generated_request.value)
        admission = _identifier(generated_admission.value)
        now = self._now()
        if (
            not isinstance(now, datetime)
            or now.tzinfo is None
            or now.utcoffset() != timedelta(0)
        ):
            raise IdentityAuthorityBootstrapUnavailable
        try:
            expires_at = now.astimezone(UTC) + self._admission_lifetime
        except (OverflowError, ValueError):
            raise IdentityAuthorityBootstrapUnavailable from None

        values = {"user": user, "workspace": workspace}
        transaction.execute(_INSERT_USER, values)
        transaction.execute(_INSERT_WORKSPACE, values)
        transaction.execute(_INSERT_AUTHORITY, values)
        transaction.execute(
            _INSERT_ADMISSION,
            {
                **values,
                "admission": admission,
                "request": request,
                "lifetime": self._lifetime_microseconds,
                "expires_at": expires_at,
            },
        )
        transaction.execute(
            _INSERT_DECISION,
            {"singleton": _SINGLETON, "admission": admission},
        )
        return BootstrappedIdentityAuthority(
            generated_user, generated_workspace, generated_admission
        )

    @staticmethod
    def _resolve(record: Row[object]) -> BootstrappedIdentityAuthority:
        if record.singleton_key != _SINGLETON:
            raise IdentityAuthorityBootstrapUnavailable
        admission = _decoded(record.admission_id)
        _decoded(record.provisioning_request)
        user = _decoded(record.target_user_id)
        workspace = _decoded(record.target_workspace_id)
        if (
            _decoded(record.foundation_user_id) != user
            or _decoded(record.foundation_workspace_id) != workspace
            or _decoded(record.authority_user_id) != user
            or _decoded(record.authority_workspace_id) != workspace
        ):
            raise IdentityAuthorityBootstrapUnavailable
        return BootstrappedIdentityAuthority(
            UserId(user), WorkspaceId(workspace), IdentityAdmissionId(admission)
        )
