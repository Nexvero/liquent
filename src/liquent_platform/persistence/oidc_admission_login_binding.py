"""Atomic offline binding of an admission to one pending OIDC login."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.persistence.identity_errors import (
    OidcLoginTransactionStoreUnavailable,
)

_LOCK_ADMISSION = text(
    "SELECT admission.target_user_id,admission.target_workspace_id,"
    " admission.expires_at,admission.consumed_at"
    " FROM identity_admissions AS admission"
    " JOIN identity_users AS target"
    " ON target.user_id=admission.target_user_id"
    " JOIN identity_workspaces AS workspace"
    " ON workspace.workspace_id=admission.target_workspace_id"
    " WHERE admission.admission_id=:admission"
    " AND target.status='active' AND workspace.status='active' FOR UPDATE"
)
_LOCK_BOUND = text(
    "SELECT state FROM oidc_login_transactions"
    " WHERE status='pending' AND admission_id=:admission"
    " AND expires_at>:now FOR UPDATE"
)
_LOCK_UNBOUND = text(
    "SELECT state FROM oidc_login_transactions"
    " WHERE status='pending' AND admission_id IS NULL"
    " AND expires_at>:now ORDER BY state FOR UPDATE"
)
_BIND = text(
    "UPDATE oidc_login_transactions SET admission_id=:admission"
    " WHERE state=:state AND status='pending' AND admission_id IS NULL"
    " AND expires_at>:now"
)


def _without_lock(statement: object) -> object:
    return text(str(statement).replace(" FOR UPDATE", ""))


def _aware(value: object) -> datetime:
    if type(value) is str:
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            raise OidcLoginTransactionStoreUnavailable from None
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise OidcLoginTransactionStoreUnavailable
    return value


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise OidcLoginTransactionStoreUnavailable
    return value.encode("utf-8")


class DatabaseOidcPendingLoginAdmissionBinding:
    """Attach one admission without accepting a browser-selected login state."""

    __slots__ = ("_engine", "_now")

    def __init__(self, engine: Engine, *, now: Callable[[], datetime]) -> None:
        self._engine = engine
        self._now = now

    def __repr__(self) -> str:
        return "DatabaseOidcPendingLoginAdmissionBinding()"

    def bind_admission(self, admission_id: IdentityAdmissionId) -> bool:
        try:
            return self._bind(admission_id)
        except OidcLoginTransactionStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise OidcLoginTransactionStoreUnavailable()

    def _bind(self, admission_id: IdentityAdmissionId) -> bool:
        admission = _encode(admission_id.value)
        now = _aware(self._now())
        with self._engine.begin() as transaction:
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                raise OidcLoginTransactionStoreUnavailable
            admission_query = self._query(transaction, _LOCK_ADMISSION)
            record = transaction.execute(
                admission_query, {"admission": admission}
            ).first()
            if (
                record is None
                or record.consumed_at is not None
                or now >= _aware(record.expires_at)
            ):
                return False

            bound = transaction.execute(
                self._query(transaction, _LOCK_BOUND),
                {"admission": admission, "now": now},
            ).all()
            if len(bound) == 1:
                return True
            if bound:
                raise OidcLoginTransactionStoreUnavailable

            candidates = transaction.execute(
                self._query(transaction, _LOCK_UNBOUND), {"now": now}
            ).all()
            if len(candidates) != 1:
                return False
            changed = transaction.execute(
                _BIND,
                {"admission": admission, "state": candidates[0].state, "now": now},
            )
            if changed.rowcount != 1:
                raise OidcLoginTransactionStoreUnavailable
            return True

    @staticmethod
    def _query(transaction: Connection, statement: object) -> object:
        return (
            statement
            if transaction.dialect.name == "postgresql"
            else _without_lock(statement)
        )
