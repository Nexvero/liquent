"""Atomic persistent supervisor cleanup retention operation bindings."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import Engine, text

from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    RetiredManifestHandoffSupervisorControlDirectory,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryCleanupDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupDisposition,
    ManifestHandoffSupervisorControlDirectoryRetentionDecisionId,
    ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention import (
    BindManifestHandoffSupervisorControlDirectoryRetentionDecision,
    BoundManifestHandoffSupervisorControlDirectoryRetentionDecision,
    EvaluateManifestHandoffSupervisorControlDirectoryRetention,
    EvaluatedManifestHandoffSupervisorControlDirectoryRetention,
    ManifestHandoffSupervisorCleanupRetentionDataClass,
    ManifestHandoffSupervisorCleanupRetentionOperationConflict,
    ManifestHandoffSupervisorCleanupRetentionOperationId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_control_directories import (
    DatabaseManifestHandoffSupervisorControlDirectories,
)


_LOCK = text(
    "LOCK TABLE manifest_handoff_supervisor_control_directories,"
    " manifest_handoff_supervisor_control_cleanup_decisions,"
    " manifest_handoff_supervisor_cleanup_retention_operations"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_DIRECTORY = text(
    "SELECT directory_id,handle_id,leaf,state,reserved_at,activated_at,retired_at"
    " FROM manifest_handoff_supervisor_control_directories"
    " WHERE directory_id=:directory"
)
_DECISION = text(
    "SELECT decision_id,directory_id,sequence_number,policy_revision_id,"
    " disposition,decided_at"
    " FROM manifest_handoff_supervisor_control_cleanup_decisions"
    " WHERE decision_id=:decision"
)
_LATEST = text(
    "SELECT sequence_number FROM manifest_handoff_supervisor_control_cleanup_decisions"
    " WHERE directory_id=:directory ORDER BY sequence_number DESC LIMIT 1"
)
_OPERATION = text(
    "SELECT operation.operation_id,operation.directory_id,operation.decision_id,"
    " operation.policy_revision_id AS operation_policy_revision_id,"
    " operation.data_class,operation.disposition AS operation_disposition,"
    " operation.evaluated_at,operation.bound_at,decision.sequence_number,"
    " decision.policy_revision_id,decision.disposition,decision.decided_at,"
    " directory.handle_id,directory.leaf,directory.state,directory.reserved_at,"
    " directory.activated_at,directory.retired_at"
    " FROM manifest_handoff_supervisor_cleanup_retention_operations operation"
    " JOIN manifest_handoff_supervisor_control_cleanup_decisions decision"
    " ON decision.decision_id=operation.decision_id"
    " AND decision.directory_id=operation.directory_id"
    " JOIN manifest_handoff_supervisor_control_directories directory"
    " ON directory.directory_id=operation.directory_id"
    " WHERE operation.operation_id=:operation"
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


class DatabaseManifestHandoffSupervisorCleanupRetentionOperations:
    """Atomically append a retention decision and its durable operation."""

    __slots__ = ("_engine", "_clock")

    def __init__(
        self,
        engine: Engine,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(engine, Engine) or (
            clock is not None and not callable(clock)
        ):
            raise ManifestHandoffRegistryUnavailable
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffSupervisorCleanupRetentionOperations()"

    def bind_control_directory_retention_decision(self, command):
        if (
            type(command)
            is not BindManifestHandoffSupervisorControlDirectoryRetentionDecision
        ):
            raise ManifestHandoffRegistryUnavailable
        evaluation = command.evaluation
        values = {
            "operation": _encode(evaluation.request.operation_id),
            "directory": _encode(evaluation.request.directory_id),
            "decision": _encode(command.decision_id),
        }

        def action(connection):
            existing = self._one(connection, _OPERATION, values, neutral=True)
            if existing is not None:
                bound = self._bound(existing)
                return (
                    bound
                    if bound.evaluation.request.directory_id
                    == evaluation.request.directory_id
                    else ManifestHandoffSupervisorCleanupRetentionOperationConflict()
                )
            collided = self._one(connection, _DECISION, values, neutral=True)
            if collided is not None:
                return ManifestHandoffSupervisorCleanupRetentionOperationConflict()
            directory = self._one(connection, _DIRECTORY, values, neutral=True)
            if directory is None:
                return None
            retired = DatabaseManifestHandoffSupervisorControlDirectories._lifecycle(
                directory
            )
            if (
                type(retired) is not RetiredManifestHandoffSupervisorControlDirectory
                or retired != evaluation.retired
            ):
                return ManifestHandoffSupervisorCleanupRetentionOperationConflict()
            latest = self._one(connection, _LATEST, values, neutral=True)
            sequence = 1 if latest is None else latest.sequence_number + 1
            if type(sequence) is not int or sequence < 1:
                raise ManifestHandoffRegistryUnavailable
            bound_at = _utc(self._clock())
            if bound_at < evaluation.evaluated_at:
                raise ManifestHandoffRegistryUnavailable
            decision = ManifestHandoffSupervisorControlDirectoryCleanupDecision(
                retired,
                command.decision_id,
                evaluation.policy_revision_id,
                evaluation.disposition,
                evaluation.evaluated_at,
            )
            connection.execute(text(
                "INSERT INTO manifest_handoff_supervisor_control_cleanup_decisions"
                " (decision_id,directory_id,sequence_number,policy_revision_id,"
                " disposition,decided_at)"
                " VALUES (:decision,:directory,:sequence,:policy,:disposition,:evaluated)"
            ), {
                **values,
                "sequence": sequence,
                "policy": _encode(evaluation.policy_revision_id),
                "disposition": evaluation.disposition.value,
                "evaluated": evaluation.evaluated_at,
            })
            connection.execute(text(
                "INSERT INTO manifest_handoff_supervisor_cleanup_retention_operations"
                " (operation_id,directory_id,decision_id,policy_revision_id,"
                " data_class,disposition,evaluated_at,bound_at)"
                " VALUES (:operation,:directory,:decision,:policy,:data_class,"
                " :disposition,:evaluated,:bound)"
            ), {
                **values,
                "policy": _encode(evaluation.policy_revision_id),
                "data_class": evaluation.data_class.value,
                "disposition": evaluation.disposition.value,
                "evaluated": evaluation.evaluated_at,
                "bound": bound_at,
            })
            return BoundManifestHandoffSupervisorControlDirectoryRetentionDecision(
                evaluation, decision
            )

        return self._write(action)

    def resolve_control_directory_retention_operation(self, operation_id):
        if type(operation_id) is not ManifestHandoffSupervisorCleanupRetentionOperationId:
            raise ManifestHandoffRegistryUnavailable
        values = {"operation": _encode(operation_id)}
        def action(connection):
            row = self._one(connection, _OPERATION, values, neutral=True)
            return None if row is None else self._bound(row)
        return self._read(action)

    @staticmethod
    def _bound(row):
        if type(row.sequence_number) is not int or row.sequence_number < 1:
            raise ManifestHandoffRegistryUnavailable
        retired = DatabaseManifestHandoffSupervisorControlDirectories._lifecycle(row)
        if type(retired) is not RetiredManifestHandoffSupervisorControlDirectory:
            raise ManifestHandoffRegistryUnavailable
        operation = ManifestHandoffSupervisorCleanupRetentionOperationId(
            _decode(row.operation_id)
        )
        directory = ManifestHandoffSupervisorControlDirectoryId(
            _decode(row.directory_id)
        )
        request = EvaluateManifestHandoffSupervisorControlDirectoryRetention(
            operation, directory
        )
        evaluation = EvaluatedManifestHandoffSupervisorControlDirectoryRetention(
            request,
            retired,
            ManifestHandoffSupervisorCleanupRetentionDataClass(row.data_class),
            ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId(
                _decode(row.operation_policy_revision_id)
            ),
            ManifestHandoffSupervisorControlDirectoryCleanupDisposition(
                row.operation_disposition
            ),
            _utc(row.evaluated_at),
        )
        decision = ManifestHandoffSupervisorControlDirectoryCleanupDecision(
            retired,
            ManifestHandoffSupervisorControlDirectoryRetentionDecisionId(
                _decode(row.decision_id)
            ),
            ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId(
                _decode(row.policy_revision_id)
            ),
            ManifestHandoffSupervisorControlDirectoryCleanupDisposition(
                row.disposition
            ),
            _utc(row.decided_at),
        )
        bound_at = _utc(row.bound_at)
        if bound_at < evaluation.evaluated_at:
            raise ManifestHandoffRegistryUnavailable
        return BoundManifestHandoffSupervisorControlDirectoryRetentionDecision(
            evaluation, decision
        )

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

    def _write(self, action):
        try:
            with self._engine.begin() as connection:
                if connection.dialect.name == "postgresql":
                    connection.execute(_LOCK)
                elif connection.dialect.name != "sqlite":
                    raise ManifestHandoffRegistryUnavailable
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
                if connection.dialect.name not in ("postgresql", "sqlite"):
                    raise ManifestHandoffRegistryUnavailable
                return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable
