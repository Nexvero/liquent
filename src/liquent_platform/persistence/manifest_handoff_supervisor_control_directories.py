"""Persistent lifecycle registry for private supervisor control directories."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import secrets

from sqlalchemy import Engine, text

from liquent_platform.identity.manifest_handoff_supervisor import ManifestHandoffSupervisorHandleId
from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    ActivateManifestHandoffSupervisorControlDirectory,
    ActiveManifestHandoffSupervisorControlDirectory,
    ManifestHandoffSupervisorControlDirectoryConflict,
    ManifestHandoffSupervisorControlDirectoryLeaf,
    ManifestHandoffSupervisorControlDirectoryState,
    ReserveManifestHandoffSupervisorControlDirectory,
    ReservedManifestHandoffSupervisorControlDirectory,
    RetireManifestHandoffSupervisorControlDirectory,
    RetiredManifestHandoffSupervisorControlDirectory,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_LOCK = text(
    "LOCK TABLE manifest_handoff_supervisor_journal_jobs,"
    " manifest_handoff_supervisor_control_directories IN SHARE ROW EXCLUSIVE MODE"
)
_BY_DIRECTORY = text(
    "SELECT directory_id,handle_id,leaf,state,reserved_at,activated_at,retired_at"
    " FROM manifest_handoff_supervisor_control_directories WHERE directory_id=:directory"
)
_BY_HANDLE = text(
    "SELECT directory_id,handle_id,leaf,state,reserved_at,activated_at,retired_at"
    " FROM manifest_handoff_supervisor_control_directories WHERE handle_id=:handle"
)
_LEAF = text(
    "SELECT directory_id FROM manifest_handoff_supervisor_control_directories WHERE leaf=:leaf"
)
_JOB = text(
    "SELECT handle_id FROM manifest_handoff_supervisor_journal_jobs WHERE handle_id=:handle"
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


def _utc(value: object) -> datetime:
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


class DatabaseManifestHandoffSupervisorControlDirectories:
    """Persist immutable bindings and forward-only lifecycle transitions."""

    __slots__ = ("_engine", "_clock", "_leaf")

    def __init__(self, engine: Engine, *, clock: Callable[[], datetime] | None = None,
                 leaf_generator: Callable[[], ManifestHandoffSupervisorControlDirectoryLeaf] | None = None) -> None:
        if not isinstance(engine, Engine):
            raise ManifestHandoffRegistryUnavailable
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._leaf = leaf_generator or (
            lambda: ManifestHandoffSupervisorControlDirectoryLeaf(secrets.token_hex(32)))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffSupervisorControlDirectories()"

    def reserve_control_directory(self, request):
        if type(request) is not ReserveManifestHandoffSupervisorControlDirectory:
            raise ManifestHandoffRegistryUnavailable
        values = {"directory": _encode(request.directory_id),
            "handle": _encode(request.handle_id)}

        def action(transaction):
            directory = transaction.execute(_BY_DIRECTORY, values).all()
            handle = transaction.execute(_BY_HANDLE, values).all()
            if directory or handle:
                if len(directory) > 1 or len(handle) > 1:
                    raise ManifestHandoffRegistryUnavailable
                row = directory[0] if directory else handle[0]
                if (directory and handle
                        and (directory[0].directory_id != handle[0].directory_id
                            or directory[0].handle_id != handle[0].handle_id)):
                    return ManifestHandoffSupervisorControlDirectoryConflict()
                reservation = self._reservation(row)
                if (reservation.directory_id == request.directory_id
                        and reservation.handle_id == request.handle_id):
                    return reservation
                return ManifestHandoffSupervisorControlDirectoryConflict()
            if transaction.execute(_JOB, values).first() is None:
                return None
            leaf = self._available_leaf(transaction)
            now = _utc(self._clock())
            transaction.execute(text(
                "INSERT INTO manifest_handoff_supervisor_control_directories"
                " (directory_id,handle_id,leaf,state,reserved_at,activated_at,retired_at)"
                " VALUES (:directory,:handle,:leaf,'reserved',:now,NULL,NULL)"
            ), {**values, "leaf": leaf.value, "now": now})
            return ReservedManifestHandoffSupervisorControlDirectory(
                request.directory_id, request.handle_id, leaf, now)

        return self._write(action)

    def activate_control_directory(self, request):
        if type(request) is not ActivateManifestHandoffSupervisorControlDirectory:
            raise ManifestHandoffRegistryUnavailable
        expected = request.reservation

        def action(transaction):
            row = self._one(transaction, _BY_DIRECTORY,
                {"directory": _encode(expected.directory_id)}, neutral=True)
            if row is None:
                return None
            if self._reservation(row) != expected:
                return ManifestHandoffSupervisorControlDirectoryConflict()
            lifecycle = self._lifecycle(row)
            if type(lifecycle) is ActiveManifestHandoffSupervisorControlDirectory:
                return lifecycle
            if type(lifecycle) is not ReservedManifestHandoffSupervisorControlDirectory:
                return ManifestHandoffSupervisorControlDirectoryConflict()
            now = _utc(self._clock())
            if now < expected.reserved_at:
                raise ManifestHandoffRegistryUnavailable
            transaction.execute(text(
                "UPDATE manifest_handoff_supervisor_control_directories"
                " SET state='active',activated_at=:now"
                " WHERE directory_id=:directory AND state='reserved'"
            ), {"directory": _encode(expected.directory_id), "now": now})
            return ActiveManifestHandoffSupervisorControlDirectory(expected, now)

        return self._write(action)

    def retire_control_directory(self, request):
        if type(request) is not RetireManifestHandoffSupervisorControlDirectory:
            raise ManifestHandoffRegistryUnavailable
        expected = request.active

        def action(transaction):
            row = self._one(transaction, _BY_DIRECTORY,
                {"directory": _encode(expected.directory_id)}, neutral=True)
            if row is None:
                return None
            lifecycle = self._lifecycle(row)
            active = lifecycle.active if type(lifecycle) is RetiredManifestHandoffSupervisorControlDirectory else lifecycle
            if active != expected:
                return ManifestHandoffSupervisorControlDirectoryConflict()
            if type(lifecycle) is RetiredManifestHandoffSupervisorControlDirectory:
                return lifecycle
            if type(lifecycle) is not ActiveManifestHandoffSupervisorControlDirectory:
                return ManifestHandoffSupervisorControlDirectoryConflict()
            now = _utc(self._clock())
            if now < expected.activated_at:
                raise ManifestHandoffRegistryUnavailable
            transaction.execute(text(
                "UPDATE manifest_handoff_supervisor_control_directories"
                " SET state='retired',retired_at=:now"
                " WHERE directory_id=:directory AND state='active'"
            ), {"directory": _encode(expected.directory_id), "now": now})
            return RetiredManifestHandoffSupervisorControlDirectory(expected, now)

        return self._write(action)

    def resolve_control_directory(self, directory_id):
        if type(directory_id) is not ManifestHandoffSupervisorControlDirectoryId:
            raise ManifestHandoffRegistryUnavailable
        return self._resolve(_BY_DIRECTORY, {"directory": _encode(directory_id)})

    def resolve_handle_control_directory(self, handle_id):
        if type(handle_id) is not ManifestHandoffSupervisorHandleId:
            raise ManifestHandoffRegistryUnavailable
        return self._resolve(_BY_HANDLE, {"handle": _encode(handle_id)})

    def _resolve(self, query, values):
        def action(connection):
            row = self._one(connection, query, values, neutral=True)
            return None if row is None else self._lifecycle(row)
        return self._read(action)

    def _available_leaf(self, transaction):
        for _ in range(4):
            leaf = self._leaf()
            if type(leaf) is not ManifestHandoffSupervisorControlDirectoryLeaf:
                raise ManifestHandoffRegistryUnavailable
            if transaction.execute(_LEAF, {"leaf": leaf.value}).first() is None:
                return leaf
        raise ManifestHandoffRegistryUnavailable

    @staticmethod
    def _one(connection, query, values, neutral=False):
        rows = connection.execute(query, values).all()
        if not rows:
            if neutral:
                return None
            raise ManifestHandoffRegistryUnavailable
        if len(rows) != 1:
            raise ManifestHandoffRegistryUnavailable
        return rows[0]

    @staticmethod
    def _reservation(row):
        return ReservedManifestHandoffSupervisorControlDirectory(
            ManifestHandoffSupervisorControlDirectoryId(_decode(row.directory_id)),
            ManifestHandoffSupervisorHandleId(_decode(row.handle_id)),
            ManifestHandoffSupervisorControlDirectoryLeaf(row.leaf),
            _utc(row.reserved_at))

    @classmethod
    def _lifecycle(cls, row):
        reservation = cls._reservation(row)
        state = ManifestHandoffSupervisorControlDirectoryState(row.state)
        if state is ManifestHandoffSupervisorControlDirectoryState.RESERVED:
            if row.activated_at is not None or row.retired_at is not None:
                raise ManifestHandoffRegistryUnavailable
            return reservation
        if row.activated_at is None:
            raise ManifestHandoffRegistryUnavailable
        active = ActiveManifestHandoffSupervisorControlDirectory(
            reservation, _utc(row.activated_at))
        if state is ManifestHandoffSupervisorControlDirectoryState.ACTIVE:
            if row.retired_at is not None:
                raise ManifestHandoffRegistryUnavailable
            return active
        if row.retired_at is None:
            raise ManifestHandoffRegistryUnavailable
        return RetiredManifestHandoffSupervisorControlDirectory(active, _utc(row.retired_at))

    def _write(self, action):
        try:
            with self._engine.begin() as connection:
                self._dialect(connection, True)
                return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable

    def _read(self, action):
        try:
            with self._engine.connect() as connection:
                self._dialect(connection, False)
                return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable

    @staticmethod
    def _dialect(connection, lock):
        if connection.dialect.name == "postgresql":
            if lock:
                connection.execute(_LOCK)
        elif connection.dialect.name != "sqlite":
            raise ManifestHandoffRegistryUnavailable
