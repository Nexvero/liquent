"""Persistent creation and single-use claim of OIDC login transactions."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, Row, text
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.oidc_trust import OidcTrustRevisionId
from liquent_platform.persistence.identity_errors import (
    OidcLoginTransactionStoreUnavailable,
)

_INSERT = text(
    "INSERT INTO oidc_login_transactions"
    " (state,status,expected_issuer,expected_nonce,code_verifier,redirect_uri,"
    " expected_trust_revision,created_at,expires_at,admission_id,return_path)"
    " VALUES (:state,'pending',:issuer,:nonce,:verifier,:redirect,:revision,:created,"
    " :expires,:admission,:return_path) ON CONFLICT (state) DO NOTHING"
)
_LOCK = text("SELECT * FROM oidc_login_transactions WHERE state=:state FOR UPDATE")
_LOCK_SQLITE = text("SELECT * FROM oidc_login_transactions WHERE state=:state")
_USE = text(
    "UPDATE oidc_login_transactions SET status='used',expected_issuer=NULL,"
    " expected_nonce=NULL,code_verifier=NULL,redirect_uri=NULL,"
    " expected_trust_revision=NULL,created_at=NULL,"
    " expires_at=NULL,admission_id=NULL,return_path=NULL"
    " WHERE state=:state AND status='pending'"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise OidcLoginTransactionStoreUnavailable
    return value.encode("utf-8")


def _optional(value: str | None) -> bytes | None:
    return None if value is None else _encode(value)


def _decode(value: object) -> str:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise OidcLoginTransactionStoreUnavailable
    try:
        result = bytes(value).decode("utf-8")
    except UnicodeDecodeError:
        raise OidcLoginTransactionStoreUnavailable from None
    if not result:
        raise OidcLoginTransactionStoreUnavailable
    return result


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


class DatabaseOidcLoginTransactions:
    """Store pending secrets once and replace them with a used-state tombstone."""

    __slots__ = ("_engine", "_now")

    def __init__(self, engine: Engine, *, now: Callable[[], datetime]) -> None:
        self._engine, self._now = engine, now

    def __repr__(self) -> str:
        return "DatabaseOidcLoginTransactions()"

    def add_transaction(
        self, state: OidcLoginState, transaction: PendingOidcLoginTransaction
    ) -> bool:
        try:
            with self._engine.begin() as connection:
                inserted = connection.execute(
                    _INSERT,
                    {
                            "state": _encode(state.value),
                            "issuer": _encode(transaction.expected_issuer),
                            "nonce": _encode(transaction.expected_nonce),
                            "verifier": _encode(transaction.code_verifier),
                            "redirect": _encode(transaction.redirect_uri),
                            "revision": _optional(
                                transaction.expected_trust_revision.value
                                if transaction.expected_trust_revision else None
                            ),
                            "created": _aware(transaction.created_at),
                            "expires": _aware(transaction.expires_at),
                            "admission": _optional(
                                transaction.admission_id.value
                                if transaction.admission_id else None
                            ),
                            "return_path": _optional(transaction.return_path),
                    },
                )
                return inserted.rowcount == 1
        except OidcLoginTransactionStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise OidcLoginTransactionStoreUnavailable

    def claim_transaction(
        self, state: OidcLoginState
    ) -> PendingOidcLoginTransaction | None:
        try:
            with self._engine.begin() as connection:
                query = (
                    _LOCK
                    if connection.dialect.name == "postgresql"
                    else _LOCK_SQLITE
                )
                parameters = {"state": _encode(state.value)}
                row = connection.execute(query, parameters).first()
                if row is None or row.status != "pending":
                    return None
                pending = self._restore(row)
                now = _aware(self._now())
                if connection.execute(_USE, parameters).rowcount != 1:
                    raise OidcLoginTransactionStoreUnavailable
                return None if now >= pending.expires_at else pending
        except OidcLoginTransactionStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise OidcLoginTransactionStoreUnavailable

    @staticmethod
    def _restore(row: Row[Any]) -> PendingOidcLoginTransaction:
        admission = (
            None
            if row.admission_id is None
            else IdentityAdmissionId(_decode(row.admission_id))
        )
        return PendingOidcLoginTransaction(
            expected_issuer=_decode(row.expected_issuer),
            expected_nonce=_decode(row.expected_nonce),
            code_verifier=_decode(row.code_verifier),
            redirect_uri=_decode(row.redirect_uri),
            created_at=_aware(row.created_at),
            expires_at=_aware(row.expires_at),
            expected_trust_revision=(
                None
                if row.expected_trust_revision is None
                else OidcTrustRevisionId(_decode(row.expected_trust_revision))
            ),
            admission_id=admission,
            return_path=None if row.return_path is None else _decode(row.return_path),
        )
