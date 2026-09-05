"""Persistent platform correlations for a controller-independent supervisor."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import Engine, text

from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffExecutionClaimId,
    ManifestHandoffExecutionOwnerId,
    ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryOwnerId,
)
from liquent_platform.identity.manifest_handoff_supervisor import (
    ManifestHandoffSupervisorHandleId,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    BindManifestHandoffSupervisorHandle,
    BoundManifestHandoffSupervisorHandle,
    ManifestHandoffSupervisorBackend,
    ManifestHandoffSupervisorBackendInstanceId,
    ManifestHandoffSupervisorBackendStatus,
    ManifestHandoffSupervisorCorrelationConflict,
    ManifestHandoffSupervisorPrepareId,
    ManifestHandoffSupervisorReleaseId,
    ManifestHandoffSupervisorTerminateId,
    ManifestHandoffSupervisorTerminalObservationId,
    RecordManifestHandoffSupervisorRelease,
    RecordManifestHandoffSupervisorTermination,
    RecordManifestHandoffSupervisorTerminalObservation,
    RecordedManifestHandoffSupervisorRelease,
    RecordedManifestHandoffSupervisorTermination,
    RecordedManifestHandoffSupervisorTerminalObservation,
    ReserveManifestHandoffRecoveryPreparation,
    ReserveManifestHandoffWriterPreparation,
    ReservedManifestHandoffRecoveryPreparation,
    ReservedManifestHandoffWriterPreparation,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_LOCK = text(
    "LOCK TABLE manifest_handoff_supervisor_backends,"
    " manifest_handoff_supervisor_preparations,"
    " manifest_handoff_supervisor_handle_bindings,"
    " manifest_handoff_supervisor_releases,"
    " manifest_handoff_supervisor_terminations,"
    " manifest_handoff_supervisor_terminal_observations,"
    " manifest_handoff_execution_claims,manifest_handoff_execution_starts,"
    " manifest_handoff_execution_ends,manifest_handoff_recovery_claims,"
    " manifest_handoff_recovery_ends IN SHARE ROW EXCLUSIVE MODE"
)
_ACTIVE_BACKENDS = text(
    "SELECT backend_instance_id,status,provisioned_at"
    " FROM manifest_handoff_supervisor_backends WHERE status='active'"
)
_BACKEND = text(
    "SELECT backend_instance_id,status FROM manifest_handoff_supervisor_backends"
    " WHERE backend_instance_id=:backend"
)
_PREPARE = text(
    "SELECT prepare_id,backend_instance_id,capability,execution_claim_id,"
    " recovery_claim_id,owner_id,reserved_at"
    " FROM manifest_handoff_supervisor_preparations WHERE prepare_id=:prepare"
)
_PREPARE_BY_EXECUTION = text(
    "SELECT prepare_id FROM manifest_handoff_supervisor_preparations"
    " WHERE execution_claim_id=:claim"
)
_PREPARE_BY_RECOVERY = text(
    "SELECT prepare_id FROM manifest_handoff_supervisor_preparations"
    " WHERE recovery_claim_id=:claim"
)
_EXECUTION_CLAIM = text(
    "SELECT claim.claim_id,claim.owner_id,end_fact.end_id"
    " FROM manifest_handoff_execution_claims claim"
    " LEFT JOIN manifest_handoff_execution_ends end_fact ON end_fact.claim_id=claim.claim_id"
    " WHERE claim.claim_id=:claim"
)
_RECOVERY_CLAIM = text(
    "SELECT claim.claim_id,claim.owner_id,claim.ended_at,end_fact.end_id"
    " FROM manifest_handoff_recovery_claims claim"
    " LEFT JOIN manifest_handoff_recovery_ends end_fact ON end_fact.claim_id=claim.claim_id"
    " WHERE claim.claim_id=:claim"
)
_HANDLE_BY_PREPARE = text(
    "SELECT handle_id,prepare_id,backend_instance_id,bound_at"
    " FROM manifest_handoff_supervisor_handle_bindings WHERE prepare_id=:prepare"
)
_HANDLE_BY_ID = text(
    "SELECT handle.handle_id,handle.prepare_id,handle.backend_instance_id,handle.bound_at,"
    " prepare.capability,prepare.execution_claim_id,prepare.recovery_claim_id,prepare.owner_id"
    " FROM manifest_handoff_supervisor_handle_bindings handle"
    " JOIN manifest_handoff_supervisor_preparations prepare"
    " ON prepare.prepare_id=handle.prepare_id AND prepare.backend_instance_id=handle.backend_instance_id"
    " WHERE handle.handle_id=:handle"
)
_WRITER_START = text(
    "SELECT 1 FROM manifest_handoff_execution_starts"
    " WHERE claim_id=:claim AND owner_id=:owner"
)
_RELEASE = text(
    "SELECT release_id,handle_id,requested_at FROM manifest_handoff_supervisor_releases"
    " WHERE release_id=:operation"
)
_RELEASE_BY_HANDLE = text(
    "SELECT release_id FROM manifest_handoff_supervisor_releases WHERE handle_id=:handle"
)
_TERMINATION = text(
    "SELECT terminate_id,handle_id,requested_at"
    " FROM manifest_handoff_supervisor_terminations WHERE terminate_id=:operation"
)
_TERMINATION_BY_HANDLE = text(
    "SELECT terminate_id FROM manifest_handoff_supervisor_terminations WHERE handle_id=:handle"
)
_TERMINAL = text(
    "SELECT terminal_observation_id,handle_id,observed_at"
    " FROM manifest_handoff_supervisor_terminal_observations"
    " WHERE terminal_observation_id=:operation"
)
_TERMINAL_BY_HANDLE = text(
    "SELECT terminal_observation_id FROM manifest_handoff_supervisor_terminal_observations"
    " WHERE handle_id=:handle"
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
        decoded = bytes(value).decode("utf-8")
    except UnicodeError:
        raise ManifestHandoffRegistryUnavailable from None
    if not decoded:
        raise ManifestHandoffRegistryUnavailable
    return decoded


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


class DatabaseManifestHandoffSupervisorCorrelations:
    """Append and resolve platform correlations without operating a process."""

    __slots__ = ("_engine", "_clock")

    def __init__(self, engine: Engine, *, clock: Callable[[], datetime] | None = None) -> None:
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffSupervisorCorrelations()"

    def resolve(self):
        def action(connection):
            rows = connection.execute(_ACTIVE_BACKENDS).all()
            if not rows:
                return None
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            row = rows[0]
            return ManifestHandoffSupervisorBackend(
                ManifestHandoffSupervisorBackendInstanceId(_decode(row.backend_instance_id)),
                ManifestHandoffSupervisorBackendStatus(row.status),
                _utc(row.provisioned_at),
            )
        return self._read(action)

    def reserve_writer(self, request):
        if type(request) is not ReserveManifestHandoffWriterPreparation:
            raise ManifestHandoffRegistryUnavailable
        return self._reserve(request, "writer")

    def reserve_recovery(self, request):
        if type(request) is not ReserveManifestHandoffRecoveryPreparation:
            raise ManifestHandoffRegistryUnavailable
        return self._reserve(request, "recovery")

    def _reserve(self, request, capability):
        values = {
            "prepare": _encode(request.prepare_id),
            "backend": _encode(request.backend_instance_id),
            "claim": _encode(request.claim_id),
            "owner": _encode(request.owner_id),
        }
        def action(transaction):
            existing = transaction.execute(_PREPARE, values).all()
            if existing:
                return self._preparation_retry(existing, request, capability, values)
            backend = transaction.execute(_BACKEND, values).all()
            if len(backend) != 1 or backend[0].status != "active":
                return None
            claim_query = _EXECUTION_CLAIM if capability == "writer" else _RECOVERY_CLAIM
            claims = transaction.execute(claim_query, values).all()
            if not claims:
                return None
            if len(claims) != 1:
                raise ManifestHandoffRegistryUnavailable
            claim = claims[0]
            if claim.owner_id != values["owner"] or claim.end_id is not None:
                return None
            if capability == "recovery" and claim.ended_at is not None:
                return None
            occupied_query = _PREPARE_BY_EXECUTION if capability == "writer" else _PREPARE_BY_RECOVERY
            if transaction.execute(occupied_query, values).first() is not None:
                return ManifestHandoffSupervisorCorrelationConflict()
            now = _utc(self._clock())
            values["now"] = now
            execution = values["claim"] if capability == "writer" else None
            recovery = values["claim"] if capability == "recovery" else None
            transaction.execute(text(
                "INSERT INTO manifest_handoff_supervisor_preparations"
                " (prepare_id,backend_instance_id,capability,execution_claim_id,"
                " recovery_claim_id,owner_id,reserved_at)"
                " VALUES (:prepare,:backend,:capability,:execution,:recovery,:owner,:now)"
            ), {**values, "capability": capability, "execution": execution, "recovery": recovery})
            return self._preparation_record(request, capability, now)
        return self._write(action)

    @staticmethod
    def _preparation_retry(rows, request, capability, values):
        if len(rows) != 1:
            raise ManifestHandoffRegistryUnavailable
        row = rows[0]
        stored_claim = row.execution_claim_id if capability == "writer" else row.recovery_claim_id
        other_claim = row.recovery_claim_id if capability == "writer" else row.execution_claim_id
        if (row.backend_instance_id != values["backend"] or row.capability != capability
                or stored_claim != values["claim"] or other_claim is not None
                or row.owner_id != values["owner"]):
            return ManifestHandoffSupervisorCorrelationConflict()
        return DatabaseManifestHandoffSupervisorCorrelations._preparation_record(
            request, capability, _utc(row.reserved_at)
        )

    @staticmethod
    def _preparation_record(request, capability, when):
        record = ReservedManifestHandoffWriterPreparation if capability == "writer" else ReservedManifestHandoffRecoveryPreparation
        return record(request.prepare_id, request.backend_instance_id, request.claim_id, request.owner_id, when)

    def bind_handle(self, request):
        if type(request) is not BindManifestHandoffSupervisorHandle:
            raise ManifestHandoffRegistryUnavailable
        values = {"prepare": _encode(request.prepare_id), "backend": _encode(request.backend_instance_id), "handle": _encode(request.handle_id)}
        def action(transaction):
            by_prepare = transaction.execute(_HANDLE_BY_PREPARE, values).all()
            if by_prepare:
                if len(by_prepare) != 1:
                    raise ManifestHandoffRegistryUnavailable
                row = by_prepare[0]
                if row.handle_id != values["handle"] or row.backend_instance_id != values["backend"]:
                    return ManifestHandoffSupervisorCorrelationConflict()
                return BoundManifestHandoffSupervisorHandle(request.prepare_id, request.backend_instance_id, request.handle_id, _utc(row.bound_at))
            preparations = transaction.execute(_PREPARE, values).all()
            if len(preparations) != 1 or preparations[0].backend_instance_id != values["backend"]:
                return None
            if transaction.execute(_HANDLE_BY_ID, values).first() is not None:
                return ManifestHandoffSupervisorCorrelationConflict()
            now = _utc(self._clock())
            transaction.execute(text(
                "INSERT INTO manifest_handoff_supervisor_handle_bindings"
                " (handle_id,prepare_id,backend_instance_id,bound_at)"
                " VALUES (:handle,:prepare,:backend,:now)"
            ), {**values, "now": now})
            return BoundManifestHandoffSupervisorHandle(request.prepare_id, request.backend_instance_id, request.handle_id, now)
        return self._write(action)

    def record_release(self, request):
        return self._operation(request, RecordManifestHandoffSupervisorRelease, _RELEASE, _RELEASE_BY_HANDLE, "release_id", "manifest_handoff_supervisor_releases", RecordedManifestHandoffSupervisorRelease, "requested_at", require_releasable=True)

    def record_termination(self, request):
        return self._operation(request, RecordManifestHandoffSupervisorTermination, _TERMINATION, _TERMINATION_BY_HANDLE, "terminate_id", "manifest_handoff_supervisor_terminations", RecordedManifestHandoffSupervisorTermination, "requested_at")

    def record_terminal_observation(self, request):
        return self._operation(request, RecordManifestHandoffSupervisorTerminalObservation, _TERMINAL, _TERMINAL_BY_HANDLE, "terminal_observation_id", "manifest_handoff_supervisor_terminal_observations", RecordedManifestHandoffSupervisorTerminalObservation, "observed_at")

    def _operation(self, request, request_type, query, by_handle, id_column, table, record_type, time_column, require_releasable=False):
        if type(request) is not request_type:
            raise ManifestHandoffRegistryUnavailable
        operation_id = getattr(request, id_column)
        values = {"operation": _encode(operation_id), "handle": _encode(request.handle_id)}
        def action(transaction):
            existing = transaction.execute(query, values).all()
            if existing:
                if len(existing) != 1:
                    raise ManifestHandoffRegistryUnavailable
                row = existing[0]
                if row.handle_id != values["handle"]:
                    return ManifestHandoffSupervisorCorrelationConflict()
                return record_type(operation_id, request.handle_id, _utc(getattr(row, time_column)))
            handles = transaction.execute(_HANDLE_BY_ID, values).all()
            if not handles:
                return None
            if len(handles) != 1:
                raise ManifestHandoffRegistryUnavailable
            handle = handles[0]
            if require_releasable:
                backend = transaction.execute(_BACKEND, {"backend": handle.backend_instance_id}).all()
                if len(backend) != 1 or backend[0].status != "active":
                    return None
                if handle.capability == "writer":
                    if transaction.execute(_WRITER_START, {"claim": handle.execution_claim_id, "owner": handle.owner_id}).first() is None:
                        return None
                elif handle.capability == "recovery":
                    claim = transaction.execute(_RECOVERY_CLAIM, {"claim": handle.recovery_claim_id}).all()
                    if len(claim) != 1 or claim[0].owner_id != handle.owner_id or claim[0].ended_at is not None or claim[0].end_id is not None:
                        return None
                else:
                    raise ManifestHandoffRegistryUnavailable
            if transaction.execute(by_handle, values).first() is not None:
                return ManifestHandoffSupervisorCorrelationConflict()
            now = _utc(self._clock())
            transaction.execute(text(
                f"INSERT INTO {table} ({id_column},handle_id,{time_column})"
                f" VALUES (:operation,:handle,:now)"
            ), {**values, "now": now})
            return record_type(operation_id, request.handle_id, now)
        return self._write(action)

    def resolve_preparation(self, prepare_id):
        if type(prepare_id) is not ManifestHandoffSupervisorPrepareId:
            raise ManifestHandoffRegistryUnavailable
        values = {"prepare": _encode(prepare_id)}
        def action(connection):
            rows = connection.execute(_PREPARE, values).all()
            if not rows:
                return None
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            row = rows[0]
            backend = ManifestHandoffSupervisorBackendInstanceId(_decode(row.backend_instance_id))
            owner = _decode(row.owner_id)
            if row.capability == "writer" and row.execution_claim_id is not None and row.recovery_claim_id is None:
                return ReservedManifestHandoffWriterPreparation(prepare_id, backend, ManifestHandoffExecutionClaimId(_decode(row.execution_claim_id)), ManifestHandoffExecutionOwnerId(owner), _utc(row.reserved_at))
            if row.capability == "recovery" and row.execution_claim_id is None and row.recovery_claim_id is not None:
                return ReservedManifestHandoffRecoveryPreparation(prepare_id, backend, ManifestHandoffRecoveryClaimId(_decode(row.recovery_claim_id)), ManifestHandoffRecoveryOwnerId(owner), _utc(row.reserved_at))
            raise ManifestHandoffRegistryUnavailable
        return self._read(action)

    def resolve_handle(self, prepare_id):
        if type(prepare_id) is not ManifestHandoffSupervisorPrepareId:
            raise ManifestHandoffRegistryUnavailable
        values = {"prepare": _encode(prepare_id)}
        def action(connection):
            rows = connection.execute(_HANDLE_BY_PREPARE, values).all()
            if not rows:
                return None
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            row = rows[0]
            return BoundManifestHandoffSupervisorHandle(prepare_id, ManifestHandoffSupervisorBackendInstanceId(_decode(row.backend_instance_id)), ManifestHandoffSupervisorHandleId(_decode(row.handle_id)), _utc(row.bound_at))
        return self._read(action)

    def resolve_release(self, release_id):
        return self._resolve_operation(release_id, ManifestHandoffSupervisorReleaseId, _RELEASE, "release_id", RecordedManifestHandoffSupervisorRelease, "requested_at")

    def resolve_termination(self, terminate_id):
        return self._resolve_operation(terminate_id, ManifestHandoffSupervisorTerminateId, _TERMINATION, "terminate_id", RecordedManifestHandoffSupervisorTermination, "requested_at")

    def resolve_terminal_observation(self, terminal_observation_id):
        return self._resolve_operation(terminal_observation_id, ManifestHandoffSupervisorTerminalObservationId, _TERMINAL, "terminal_observation_id", RecordedManifestHandoffSupervisorTerminalObservation, "observed_at")

    def _resolve_operation(self, operation_id, id_type, query, id_column, record_type, time_column):
        if type(operation_id) is not id_type:
            raise ManifestHandoffRegistryUnavailable
        values = {"operation": _encode(operation_id)}
        def action(connection):
            rows = connection.execute(query, values).all()
            if not rows:
                return None
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            row = rows[0]
            return record_type(operation_id, ManifestHandoffSupervisorHandleId(_decode(row.handle_id)), _utc(getattr(row, time_column)))
        return self._read(action)

    def _write(self, action):
        try:
            with self._engine.begin() as transaction:
                self._dialect(transaction, lock=True)
                return action(transaction)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable

    def _read(self, action):
        try:
            with self._engine.connect() as connection:
                self._dialect(connection, lock=False)
                return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable

    @staticmethod
    def _dialect(connection, *, lock):
        if connection.dialect.name == "postgresql":
            if lock:
                connection.execute(_LOCK)
        elif connection.dialect.name != "sqlite":
            raise ManifestHandoffRegistryUnavailable
