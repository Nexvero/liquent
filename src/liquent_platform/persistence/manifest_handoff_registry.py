"""Atomic persistent reservation and authorized lookup of manifest handoffs."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import Connection, Engine, Row, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffAttemptId,
    ManifestHandoffAttemptView,
    ManifestHandoffName,
    ManifestHandoffObservationId,
    ManifestHandoffObservationKind,
    ManifestHandoffRegistryScopeId,
    ManifestHandoffReservationConflict,
    ManifestHandoffReservationId,
    ReservedManifestHandoffAttempt,
)
from liquent_platform.persistence.identity_errors import (
    ManifestHandoffRegistryUnavailable,
)


_LOCK = text(
    "LOCK TABLE identity_users,manifest_handoff_registry_scopes,"
    " manifest_handoff_registry_authorities,manifest_handoff_attempts,"
    " manifest_handoff_attempt_observations IN SHARE ROW EXCLUSIVE MODE"
)
_EXISTING_RESERVATION = text(
    "SELECT attempt.attempt_id,attempt.reservation_id,attempt.scope_id,"
    " attempt.actor_user_id,attempt.handoff_name,attempt.reserved_at,"
    " observation.observation_id,observation.kind,observation.sequence_number"
    " FROM manifest_handoff_attempts attempt"
    " LEFT JOIN manifest_handoff_attempt_observations observation"
    " ON observation.attempt_id=attempt.attempt_id"
    " AND observation.sequence_number=1"
    " WHERE attempt.reservation_id=:reservation"
)
_CURRENT_AUTHORITY = text(
    "SELECT 1 FROM identity_users user_fact"
    " JOIN manifest_handoff_registry_authorities authority"
    " ON authority.user_id=user_fact.user_id AND authority.scope_id=:scope"
    " JOIN manifest_handoff_registry_scopes scope"
    " ON scope.scope_id=authority.scope_id"
    " WHERE user_fact.user_id=:actor AND user_fact.status='active'"
    " AND scope.status='active' AND authority.status='active'"
)
_NAME_OCCUPIED = text(
    "SELECT 1 FROM manifest_handoff_attempts"
    " WHERE scope_id=:scope AND handoff_name=:name"
)
_ATTEMPT_VIEW = text(
    "SELECT attempt.attempt_id,attempt.scope_id,attempt.actor_user_id,"
    " attempt.handoff_name,attempt.reserved_at,observation.kind"
    " FROM manifest_handoff_attempts attempt"
    " LEFT JOIN manifest_handoff_attempt_observations observation"
    " ON observation.attempt_id=attempt.attempt_id"
    " AND observation.sequence_number=("
    " SELECT MAX(latest.sequence_number)"
    " FROM manifest_handoff_attempt_observations latest"
    " WHERE latest.attempt_id=attempt.attempt_id)"
    " WHERE attempt.scope_id=:scope AND attempt.handoff_name=:name"
)


def _encode(value: object) -> bytes:
    raw = value.value if hasattr(value, "value") else value
    if type(raw) is not str or not raw:
        raise ManifestHandoffRegistryUnavailable
    return raw.encode("utf-8")


def _decode(value: object) -> str:
    try:
        if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
            raise ManifestHandoffRegistryUnavailable
        result = bytes(value).decode("utf-8")
    except UnicodeError:
        raise ManifestHandoffRegistryUnavailable from None
    if not result:
        raise ManifestHandoffRegistryUnavailable
    return result


def _stored_utc(value: object) -> datetime:
    if type(value) is str:
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            raise ManifestHandoffRegistryUnavailable from None
    if type(value) is not datetime:
        raise ManifestHandoffRegistryUnavailable
    value = value.replace(tzinfo=value.tzinfo or timezone.utc)
    if value.utcoffset() != timedelta(0):
        raise ManifestHandoffRegistryUnavailable
    return value


def _current_utc(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if type(value) is not datetime or value.tzinfo is None:
        raise ManifestHandoffRegistryUnavailable
    if value.utcoffset() != timedelta(0):
        raise ManifestHandoffRegistryUnavailable
    return value


class DatabaseManifestHandoffRegistry:
    """Reserve names permanently and expose current-authority-bound views."""

    __slots__ = ("_engine", "_attempt_id", "_observation_id", "_clock")

    def __init__(
        self,
        engine: Engine,
        *,
        generate_attempt_id: Callable[[], ManifestHandoffAttemptId],
        generate_observation_id: Callable[[], ManifestHandoffObservationId],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._engine = engine
        self._attempt_id = generate_attempt_id
        self._observation_id = generate_observation_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffRegistry()"

    def reserve_attempt(
        self, reservation_id, actor_user_id, scope_id, handoff_name
    ):
        try:
            if not all((
                type(reservation_id) is ManifestHandoffReservationId,
                type(actor_user_id) is str and bool(actor_user_id),
                type(scope_id) is ManifestHandoffRegistryScopeId,
                type(handoff_name) is ManifestHandoffName,
            )):
                raise ManifestHandoffRegistryUnavailable
            values = {
                "reservation": _encode(reservation_id),
                "actor": _encode(actor_user_id),
                "scope": _encode(scope_id),
                "name": handoff_name.value,
            }
            with self._engine.begin() as transaction:
                return self._reserve(
                    transaction, reservation_id, actor_user_id,
                    scope_id, handoff_name, values,
                )
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable

    def _reserve(
        self, transaction: Connection, reservation_id, actor_user_id,
        scope_id, handoff_name, values,
    ):
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise ManifestHandoffRegistryUnavailable

        existing = transaction.execute(_EXISTING_RESERVATION, values).all()
        if existing:
            return self._retry(
                existing, reservation_id, actor_user_id, scope_id, handoff_name, values
            )
        if transaction.execute(_CURRENT_AUTHORITY, values).first() is None:
            return None
        if transaction.execute(_NAME_OCCUPIED, values).first() is not None:
            return ManifestHandoffReservationConflict()

        attempt_id = self._attempt_id()
        observation_id = self._observation_id()
        now = _current_utc(self._clock)
        if (
            type(attempt_id) is not ManifestHandoffAttemptId
            or type(observation_id) is not ManifestHandoffObservationId
        ):
            raise ManifestHandoffRegistryUnavailable
        values.update(
            attempt=_encode(attempt_id), observation=_encode(observation_id), now=now
        )
        transaction.execute(text(
            "INSERT INTO manifest_handoff_attempts"
            " (attempt_id,reservation_id,scope_id,actor_user_id,handoff_name,reserved_at)"
            " VALUES (:attempt,:reservation,:scope,:actor,:name,:now)"
        ), values)
        transaction.execute(text(
            "INSERT INTO manifest_handoff_attempt_observations"
            " (observation_id,attempt_id,sequence_number,kind,manifest_sha256,"
            " file_count,observed_at)"
            " VALUES (:observation,:attempt,1,'reserved',NULL,NULL,:now)"
        ), values)
        return ReservedManifestHandoffAttempt(
            reservation_id, attempt_id, scope_id, actor_user_id, handoff_name, now
        )

    @staticmethod
    def _retry(
        rows, reservation_id, actor_user_id, scope_id, handoff_name, values
    ):
        if len(rows) != 1:
            raise ManifestHandoffRegistryUnavailable
        row = rows[0]
        if (
            row.reservation_id != values["reservation"]
            or row.scope_id != values["scope"]
            or row.actor_user_id != values["actor"]
            or row.handoff_name != values["name"]
        ):
            return ManifestHandoffReservationConflict()
        if row.sequence_number != 1 or row.kind != "reserved":
            raise ManifestHandoffRegistryUnavailable
        try:
            attempt_id = ManifestHandoffAttemptId(_decode(row.attempt_id))
            _ = ManifestHandoffObservationId(_decode(row.observation_id))
        except ValueError:
            raise ManifestHandoffRegistryUnavailable from None
        return ReservedManifestHandoffAttempt(
            reservation_id,
            attempt_id,
            scope_id,
            actor_user_id,
            handoff_name,
            _stored_utc(row.reserved_at),
        )

    def get_attempt(self, actor_user_id, scope_id, handoff_name):
        try:
            if not all((
                type(actor_user_id) is str and bool(actor_user_id),
                type(scope_id) is ManifestHandoffRegistryScopeId,
                type(handoff_name) is ManifestHandoffName,
            )):
                raise ManifestHandoffRegistryUnavailable
            values = {
                "actor": _encode(actor_user_id),
                "scope": _encode(scope_id),
                "name": handoff_name.value,
            }
            with self._engine.connect() as connection:
                if connection.dialect.name not in {"sqlite", "postgresql"}:
                    raise ManifestHandoffRegistryUnavailable
                if connection.execute(_CURRENT_AUTHORITY, values).first() is None:
                    return None
                rows = connection.execute(_ATTEMPT_VIEW, values).all()
            if not rows:
                return None
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            return self._view(rows[0])
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable

    @staticmethod
    def _view(row: Row) -> ManifestHandoffAttemptView:
        try:
            return ManifestHandoffAttemptView(
                ManifestHandoffAttemptId(_decode(row.attempt_id)),
                ManifestHandoffRegistryScopeId(_decode(row.scope_id)),
                UserId(_decode(row.actor_user_id)),
                ManifestHandoffName(row.handoff_name),
                ManifestHandoffObservationKind(row.kind),
                _stored_utc(row.reserved_at),
            )
        except (TypeError, ValueError):
            raise ManifestHandoffRegistryUnavailable from None
