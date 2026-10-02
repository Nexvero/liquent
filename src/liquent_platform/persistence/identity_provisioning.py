"""Persistent, retry-safe identity-admission provisioning."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Connection, Engine, Row, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    ProvisioningRequestId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.identity_errors import (
    IdentityAdmissionProvisioningConflict,
    IdentityAdmissionStoreUnavailable,
)

_MICROSECOND = timedelta(microseconds=1)
_MAX_BIGINT = 2**63 - 1
_PROVISIONING_REQUEST_CONSTRAINT = "uq_identity_admissions_provisioning_request"

_SELECT_ADMISSION = text(
    "SELECT admission_id, target_user_id, target_workspace_id,"
    " lifetime_microseconds FROM identity_admissions"
    " WHERE provisioning_request = :request"
)
_INSERT_ADMISSION = text(
    "INSERT INTO identity_admissions"
    " (admission_id, provisioning_request, target_user_id,"
    " target_workspace_id, lifetime_microseconds, expires_at,"
    " consumed_at, bound_issuer, bound_subject)"
    " VALUES (:admission, :request, :user, :workspace, :lifetime,"
    " :expires, NULL, NULL, NULL)"
)


def _encode(value: object) -> bytes:
    """Return exact non-empty UTF-8 bytes or fail neutrally."""

    if type(value) is not str or not value:
        raise IdentityAdmissionStoreUnavailable
    try:
        return value.encode("utf-8")
    except UnicodeEncodeError:
        raise IdentityAdmissionStoreUnavailable from None


def _decode(value: object) -> str:
    """Return exact non-empty stored UTF-8 text or fail neutrally."""
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise IdentityAdmissionStoreUnavailable
    try:
        decoded = bytes(value).decode("utf-8")
    except UnicodeDecodeError:
        raise IdentityAdmissionStoreUnavailable from None
    if not decoded:
        raise IdentityAdmissionStoreUnavailable
    return decoded


def _lifetime_microseconds(value: object) -> int:
    """Validate a positive, exactly represented timedelta."""

    if type(value) is not timedelta or value <= timedelta(0):
        raise IdentityAdmissionStoreUnavailable
    microseconds = value // _MICROSECOND
    if microseconds <= 0 or microseconds > _MAX_BIGINT:
        raise IdentityAdmissionStoreUnavailable
    return microseconds


def _aware(value: object) -> datetime:
    """Accept only a timezone-aware clock result."""
    if not isinstance(value, datetime):
        raise IdentityAdmissionStoreUnavailable
    if value.tzinfo is None or value.utcoffset() is None:
        raise IdentityAdmissionStoreUnavailable
    return value


def _is_request_race(error: IntegrityError) -> bool:
    """Recognize only the named provisioning-request constraint."""
    diagnostic = getattr(error.orig, "diag", None)
    return (
        getattr(diagnostic, "constraint_name", None)
        == _PROVISIONING_REQUEST_CONSTRAINT
    )


class DatabaseIdentityAdmissionProvisioningStore:
    """Provision admissions atomically through an injected database engine."""

    __slots__ = ("_engine", "_now", "_generate_admission_id")

    def __init__(
        self,
        engine: Engine,
        *,
        now: Callable[[], datetime],
        generate_admission_id: Callable[[], IdentityAdmissionId],
    ) -> None:
        self._engine = engine
        self._now = now
        self._generate_admission_id = generate_admission_id

    def __repr__(self) -> str:
        return "DatabaseIdentityAdmissionProvisioningStore()"

    def provision_admission(
        self,
        request_id: ProvisioningRequestId,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
        lifetime: timedelta,
    ) -> IdentityAdmissionId:
        """Create one admission or return the exact prior result."""

        try:
            with self._engine.begin() as transaction:
                return self._provision(
                    transaction,
                    request_id,
                    target_user_id,
                    target_workspace_id,
                    lifetime,
                )
        except IdentityAdmissionProvisioningConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = IdentityAdmissionProvisioningConflict
        except IdentityAdmissionStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = IdentityAdmissionStoreUnavailable
        except Exception:
            failure = IdentityAdmissionStoreUnavailable
        raise failure()

    def _provision(
        self,
        transaction: Connection,
        request_id: ProvisioningRequestId,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
        lifetime: timedelta,
    ) -> IdentityAdmissionId:
        request = _encode(request_id.value)
        user = _encode(target_user_id)
        workspace = _encode(target_workspace_id)
        lifetime_us = _lifetime_microseconds(lifetime)

        existing = self._find(transaction, request)
        if existing is not None:
            return self._compare(existing, user, workspace, lifetime_us)

        now = _aware(self._now())
        generated = self._generate_admission_id()
        if type(generated) is not IdentityAdmissionId:
            raise IdentityAdmissionStoreUnavailable
        admission = _encode(generated.value)
        expires = _aware(now + lifetime)

        savepoint = transaction.begin_nested()
        request_race = False
        try:
            transaction.execute(
                _INSERT_ADMISSION,
                {
                    "admission": admission,
                    "request": request,
                    "user": user,
                    "workspace": workspace,
                    "lifetime": lifetime_us,
                    "expires": expires,
                },
            )
        except IntegrityError as error:
            savepoint.rollback()
            if not _is_request_race(error):
                raise
            request_race = True
        else:
            savepoint.commit()

        if request_race:
            winner = self._find(transaction, request)
            if winner is None:
                raise IdentityAdmissionStoreUnavailable
            return self._compare(winner, user, workspace, lifetime_us)
        return generated

    @staticmethod
    def _find(transaction: Connection, request: bytes) -> Row[Any] | None:
        """Load one request without locking or changing its state."""
        return transaction.execute(_SELECT_ADMISSION, {"request": request}).first()

    @staticmethod
    def _compare(
        record: Row[Any], user: bytes, workspace: bytes, lifetime_us: int
    ) -> IdentityAdmissionId:
        """Return an exact replay, or report conflicting business input."""

        admission = IdentityAdmissionId(_decode(record.admission_id))
        stored_user = _decode(record.target_user_id)
        stored_workspace = _decode(record.target_workspace_id)
        stored_lifetime = record.lifetime_microseconds
        if (
            stored_user != user.decode("utf-8")
            or stored_workspace != workspace.decode("utf-8")
            or type(stored_lifetime) is not int
            or stored_lifetime <= 0
            or stored_lifetime != lifetime_us
        ):
            raise IdentityAdmissionProvisioningConflict
        return admission
