"""Retry-safe persistence for internally authorized identity admissions."""

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
_REQUEST_CONSTRAINT = "uq_identity_admissions_provisioning_request"

_LOCK_REQUEST = text(
    "SELECT admission_id, target_user_id, target_workspace_id,"
    " lifetime_microseconds FROM identity_admissions"
    " WHERE provisioning_request = :request FOR UPDATE"
)
_INSERT_ADMISSION = text(
    "INSERT INTO identity_admissions"
    " (admission_id, provisioning_request, target_user_id,"
    " target_workspace_id, lifetime_microseconds, expires_at, consumed_at,"
    " bound_issuer, bound_subject)"
    " VALUES (:admission, :request, :user, :workspace, :lifetime, :expires_at,"
    " NULL, NULL, NULL)"
)


def _encode(value: object) -> bytes:
    """Return exact non-empty UTF-8 bytes or refuse technically."""

    if type(value) is not str or not value:
        raise IdentityAdmissionStoreUnavailable
    return value.encode("utf-8")


def _stored_bytes(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise IdentityAdmissionStoreUnavailable
    stored = bytes(value)
    if not stored:
        raise IdentityAdmissionStoreUnavailable
    return stored


def _decode(value: object) -> str:
    try:
        decoded = _stored_bytes(value).decode("utf-8")
    except UnicodeDecodeError:
        raise IdentityAdmissionStoreUnavailable from None
    if not decoded:
        raise IdentityAdmissionStoreUnavailable
    return decoded


def _aware(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise IdentityAdmissionStoreUnavailable
    if value.tzinfo is None or value.utcoffset() is None:
        raise IdentityAdmissionStoreUnavailable
    return value


def _lifetime_microseconds(value: object) -> int:
    if type(value) is not timedelta or value <= timedelta(0):
        raise IdentityAdmissionStoreUnavailable
    microseconds = value // _MICROSECOND
    if microseconds <= 0 or microseconds > _MAX_BIGINT:
        raise IdentityAdmissionStoreUnavailable
    return microseconds


def _is_request_race(error: IntegrityError) -> bool:
    diagnostic = getattr(error.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None) == _REQUEST_CONSTRAINT


class DatabaseIdentityAdmissionProvisioningStore:
    """Persist one admission per stable internal provisioning request."""

    __slots__ = ("_engine", "_generate_admission_id", "_now")

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
        """Create once or resolve an exact retry without changing stored state."""

        try:
            return self._provision(
                request_id, target_user_id, target_workspace_id, lifetime
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
        # Outside every handler: no driver, clock, generator, or prior neutral
        # exception remains attached as a context chain.
        raise failure()

    def _provision(
        self,
        request_id: ProvisioningRequestId,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
        lifetime: timedelta,
    ) -> IdentityAdmissionId:
        request = _encode(request_id.value)
        user = _encode(target_user_id)
        workspace = _encode(target_workspace_id)
        duration = _lifetime_microseconds(lifetime)

        with self._engine.begin() as transaction:
            existing = transaction.execute(
                _LOCK_REQUEST, {"request": request}
            ).first()
            if existing is not None:
                return self._resolve(existing, user, workspace, duration)

            now = _aware(self._now())
            generated = self._generate_admission_id()
            if type(generated) is not IdentityAdmissionId:
                raise IdentityAdmissionStoreUnavailable
            admission = _encode(generated.value)
            try:
                expires_at = _aware(now + lifetime)
            except (OverflowError, ValueError):
                raise IdentityAdmissionStoreUnavailable from None

            savepoint = transaction.begin_nested()
            try:
                transaction.execute(
                    _INSERT_ADMISSION,
                    {
                        "admission": admission,
                        "request": request,
                        "user": user,
                        "workspace": workspace,
                        "lifetime": duration,
                        "expires_at": expires_at,
                    },
                )
            except IntegrityError as error:
                savepoint.rollback()
                if not _is_request_race(error):
                    raise
                winner = transaction.execute(
                    _LOCK_REQUEST, {"request": request}
                ).first()
                if winner is None:
                    raise IdentityAdmissionStoreUnavailable
                return self._resolve(winner, user, workspace, duration)
            savepoint.commit()
            return generated

    @staticmethod
    def _resolve(
        record: Row[Any],
        user: bytes,
        workspace: bytes,
        lifetime_microseconds: int,
    ) -> IdentityAdmissionId:
        stored_admission = _decode(record.admission_id)
        stored_user = _stored_bytes(record.target_user_id)
        stored_workspace = _stored_bytes(record.target_workspace_id)
        stored_lifetime = record.lifetime_microseconds
        if type(stored_lifetime) is not int or stored_lifetime <= 0:
            raise IdentityAdmissionStoreUnavailable
        if (
            stored_user != user
            or stored_workspace != workspace
            or stored_lifetime != lifetime_microseconds
        ):
            raise IdentityAdmissionProvisioningConflict
        return IdentityAdmissionId(stored_admission)
