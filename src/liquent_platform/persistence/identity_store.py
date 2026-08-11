"""Persistent external-identity lookup and atomic admission consumption."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy import Connection, Engine, Row, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.persistence.identity_errors import (
    ExternalIdentityStoreUnavailable,
)

# Losing one of these is ordinary concurrency the database decided. Any other
# violation is left unclassified and stays technical.
_BINDING_CONFLICTS = frozenset(
    {"pk_external_identity_bindings", "uq_external_identity_bindings_user_id"}
)

# The admission row is always locked first, so two participants order themselves
# identically and no lock cycle can form. PostgreSQL is the normative runtime;
# there is no dialect branch that would present another database as equivalent.
_LOCK_ADMISSION = text(
    "SELECT target_user_id, expires_at, consumed_at, bound_issuer, bound_subject"
    " FROM identity_admissions WHERE admission_id = :admission FOR UPDATE"
)
_SELECT_BINDING = text(
    "SELECT user_id FROM external_identity_bindings"
    " WHERE issuer = :issuer AND subject = :subject"
)
_SELECT_USER_BOUND = text(
    "SELECT 1 FROM external_identity_bindings WHERE user_id = :user"
)
_INSERT_BINDING = text(
    "INSERT INTO external_identity_bindings (issuer, subject, user_id)"
    " VALUES (:issuer, :subject, :user)"
)
_CONSUME_ADMISSION = text(
    "UPDATE identity_admissions"
    " SET consumed_at = :now, bound_issuer = :issuer, bound_subject = :subject"
    " WHERE admission_id = :admission AND consumed_at IS NULL"
)


def _encode(value: object) -> bytes:
    """Exact UTF-8 bytes of a non-empty str; nothing else is storable."""

    if type(value) is not str or not value:
        raise ExternalIdentityStoreUnavailable
    return value.encode("utf-8")


def _decode(value: object) -> str:
    """Exact text of stored bytes; anything else is structurally unusable."""

    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise ExternalIdentityStoreUnavailable
    try:
        decoded = bytes(value).decode("utf-8")
    except UnicodeDecodeError:
        # Never replaced and never normalised: unreadable bytes are a fault.
        raise ExternalIdentityStoreUnavailable from None
    if not decoded:
        raise ExternalIdentityStoreUnavailable
    return decoded


def _aware(value: object) -> datetime:
    """A stored or generated instant that can bound validity, or a refusal."""

    if not isinstance(value, datetime):
        raise ExternalIdentityStoreUnavailable
    if value.tzinfo is None or value.utcoffset() is None:
        # A naive instant is never reinterpreted as UTC.
        raise ExternalIdentityStoreUnavailable
    return value


def _is_binding_conflict(error: IntegrityError) -> bool:
    """True only for a constraint this boundary knows as normal concurrency.

    Read from the driver's structured diagnostics, never by parsing a freely
    worded message. Without a constraint name nothing is classified, so an
    unexpected violation cannot be mistaken for a business decision.
    """

    name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
    return name in _BINDING_CONFLICTS


class DatabaseExternalIdentities:
    """Identity lookup and atomic admission consumption on one database.

    The database is the security boundary: single-use consumption and the first
    binding are decided by row locking and unique constraints inside **one**
    transaction, never by a check-then-act sequence and never by an in-process
    lock. The engine is injected and never closed here; its lifecycle belongs to
    the composition root. Provisioning is deliberately absent (LQ-181).
    """

    __slots__ = ("_engine", "_now")

    def __init__(self, engine: Engine, *, now: Callable[[], datetime]) -> None:
        self._engine = engine
        self._now = now

    def __repr__(self) -> str:
        # Constant and value-free: no engine, DSN, clock, or stored data.
        return "DatabaseExternalIdentities()"

    def get_user_id(self, identity: ExternalIdentity) -> UserId | None:
        """Resolve one exact external identity, read-only and clock-free."""

        try:
            return self._lookup(identity)
        except ExternalIdentityStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        # Raised outside every handler, so neither cause nor context escapes.
        raise ExternalIdentityStoreUnavailable

    def consume_admission_and_bind(
        self,
        admission_id: IdentityAdmissionId,
        identity: ExternalIdentity,
    ) -> UserId | None:
        """Consume one admission and create its first binding, or refuse."""

        try:
            with self._engine.begin() as transaction:
                return self._decide(transaction, admission_id, identity)
        except ExternalIdentityStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            # Engine, transaction, decoding, and clock faults alike. A deadlock
            # or serialization failure is technical too and is never retried.
            pass
        raise ExternalIdentityStoreUnavailable

    def _lookup(self, identity: ExternalIdentity) -> UserId | None:
        issuer, subject = _encode(identity.issuer), _encode(identity.subject)
        with self._engine.connect() as connection:
            row = connection.execute(
                _SELECT_BINDING, {"issuer": issuer, "subject": subject}
            ).first()
        return None if row is None else UserId(_decode(row[0]))

    def _decide(
        self,
        transaction: Connection,
        admission_id: IdentityAdmissionId,
        identity: ExternalIdentity,
    ) -> UserId | None:
        admission = _encode(admission_id.value)
        issuer, subject = _encode(identity.issuer), _encode(identity.subject)
        record = transaction.execute(
            _LOCK_ADMISSION, {"admission": admission}
        ).first()
        if record is None:
            return None  # unknown admission; no clock read
        target = UserId(_decode(record.target_user_id))

        if record.consumed_at is not None:
            # A consumed instant passes the same aware boundary as every other
            # stored time before it may support an idempotent answer. No clock
            # read and no expiry comparison happen here.
            _aware(record.consumed_at)
            return self._repeat(transaction, record, target, identity)

        if transaction.execute(
            _SELECT_BINDING, {"issuer": issuer, "subject": subject}
        ).first():
            return None  # already bound; the admission stays untouched
        if transaction.execute(
            _SELECT_USER_BOUND, {"user": record.target_user_id}
        ).first():
            return None  # the target already carries another identity

        now = _aware(self._now())
        if now >= _aware(record.expires_at):
            return None  # expired, also exactly at expiry; state unchanged

        savepoint = transaction.begin_nested()
        try:
            transaction.execute(
                _INSERT_BINDING,
                {
                    "issuer": issuer,
                    "subject": subject,
                    "user": record.target_user_id,
                },
            )
        except IntegrityError as error:
            # Rolled back to the savepoint so the outer transaction stays
            # usable; work never continues inside a failed one.
            savepoint.rollback()
            if not _is_binding_conflict(error):
                raise
            return None
        savepoint.commit()
        # The same instant bounds both facts, and both commit together.
        consumed = transaction.execute(
            _CONSUME_ADMISSION,
            {
                "now": now,
                "issuer": issuer,
                "subject": subject,
                "admission": admission,
            },
        )
        if consumed.rowcount != 1:
            # The row is already locked, so anything but one hit is a broken
            # internal invariant rather than ordinary concurrency. Raising
            # rolls the whole transaction back: no binding survives and the
            # admission stays open. No retry and no second clock read.
            raise ExternalIdentityStoreUnavailable
        return target

    def _repeat(
        self,
        transaction: Connection,
        record: Row[Any],
        target: UserId,
        identity: ExternalIdentity,
    ) -> UserId | None:
        """An already consumed admission: exact repeat, or neutral refusal."""

        if (
            _decode(record.bound_issuer) != identity.issuer
            or _decode(record.bound_subject) != identity.subject
        ):
            return None  # consumed for a different identity
        bound = transaction.execute(
            _SELECT_BINDING,
            {
                "issuer": _encode(identity.issuer),
                "subject": _encode(identity.subject),
            },
        ).first()
        if bound is None or _decode(bound[0]) != str(target):
            # A consumed record whose binding is missing or points at another
            # user is structural corruption, never a business rejection.
            raise ExternalIdentityStoreUnavailable
        return target
