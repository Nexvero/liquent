"""Persistent cleanup decisions and attempt lifecycle facts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    RetiredManifestHandoffSupervisorControlDirectory,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    CleanupManifestHandoffSupervisorControlDirectory,
    CompletedManifestHandoffSupervisorControlDirectoryCleanup,
    ManifestHandoffSupervisorControlDirectoryCleanupAttemptId,
    ManifestHandoffSupervisorControlDirectoryCleanupConflict,
    ManifestHandoffSupervisorControlDirectoryCleanupDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupDisposition,
    ManifestHandoffSupervisorControlDirectoryCleanupOutcome,
    ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome,
    ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired,
    ManifestHandoffSupervisorControlDirectoryRetentionDecisionId,
    ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
    ReconcileManifestHandoffSupervisorControlDirectoryCleanup,
    ReconciledManifestHandoffSupervisorControlDirectoryCleanup,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_clearance import (
    ManifestHandoffSupervisorControlDirectoryCleanupClearanceId,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_execution import (
    ClaimedManifestHandoffSupervisorControlDirectoryCleanup,
    ManifestHandoffSupervisorControlDirectoryCleanupPreflightId,
    ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId,
    PreparedManifestHandoffSupervisorControlDirectoryCleanup,
    RemovedManifestHandoffSupervisorControlDirectory,
    UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_control_directories import (
    DatabaseManifestHandoffSupervisorControlDirectories,
)


_LOCK = text(
    "LOCK TABLE identity_users,manifest_handoff_supervisor_control_directories,"
    " manifest_handoff_supervisor_control_cleanup_decisions,"
    " manifest_handoff_supervisor_control_cleanup_attempts,"
    " manifest_handoff_supervisor_control_cleanup_write_claims"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_DIRECTORY = text(
    "SELECT directory_id,handle_id,leaf,state,reserved_at,activated_at,retired_at"
    " FROM manifest_handoff_supervisor_control_directories"
    " WHERE directory_id=:directory"
)
_DECISION = text(
    "SELECT decision.decision_id,decision.directory_id,decision.sequence_number,"
    " decision.policy_revision_id,decision.disposition,decision.decided_at,"
    " directory.handle_id,directory.leaf,directory.state,directory.reserved_at,"
    " directory.activated_at,directory.retired_at"
    " FROM manifest_handoff_supervisor_control_cleanup_decisions decision"
    " JOIN manifest_handoff_supervisor_control_directories directory"
    " ON directory.directory_id=decision.directory_id"
    " WHERE decision.decision_id=:decision"
)
_LATEST_DECISION = text(
    "SELECT decision.decision_id,decision.directory_id,decision.sequence_number,"
    " decision.policy_revision_id,decision.disposition,decision.decided_at,"
    " directory.handle_id,directory.leaf,directory.state,directory.reserved_at,"
    " directory.activated_at,directory.retired_at"
    " FROM manifest_handoff_supervisor_control_cleanup_decisions decision"
    " JOIN manifest_handoff_supervisor_control_directories directory"
    " ON directory.directory_id=decision.directory_id"
    " WHERE decision.directory_id=:directory"
    " ORDER BY decision.sequence_number DESC LIMIT 1"
)
_ATTEMPT = text(
    "SELECT attempt.attempt_id,attempt.directory_id,attempt.actor_user_id,"
    " attempt.decision_id,attempt.state,attempt.started_at,attempt.unknown_at,"
    " attempt.outcome,attempt.completed_at,attempt.reconciliation_outcome,"
    " attempt.reconciled_at,attempt.write_claimed_at,"
    " claim.claim_id,claim.clearance_id,claim.preflight_id,claim.prepared_at,claim.claimed_at,"
    " decision.decided_at AS decision_decided_at"
    " FROM manifest_handoff_supervisor_control_cleanup_attempts attempt"
    " JOIN manifest_handoff_supervisor_control_cleanup_decisions decision"
    " ON decision.decision_id=attempt.decision_id"
    " AND decision.directory_id=attempt.directory_id"
    " LEFT JOIN manifest_handoff_supervisor_control_cleanup_write_claims claim"
    " ON claim.attempt_id=attempt.attempt_id AND claim.directory_id=attempt.directory_id"
    " WHERE attempt.attempt_id=:attempt"
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


class DatabaseManifestHandoffSupervisorControlDirectoryCleanup:
    """Persist decisions and forward-only cleanup attempt states."""

    __slots__ = ("_engine", "_clock")

    def __init__(self, engine: Engine, *, clock: Callable[[], datetime] | None = None) -> None:
        if not isinstance(engine, Engine) or (clock is not None and not callable(clock)):
            raise ManifestHandoffRegistryUnavailable
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffSupervisorControlDirectoryCleanup()"

    def record_cleanup_decision(self, decision):
        if type(decision) is not ManifestHandoffSupervisorControlDirectoryCleanupDecision:
            raise ManifestHandoffRegistryUnavailable

        def action(transaction):
            values = {"decision": _encode(decision.decision_id),
                "directory": _encode(decision.directory_id)}
            existing = self._one(transaction, _DECISION, values, neutral=True)
            if existing is not None:
                current = self._decision(existing)
                return current if current == decision else ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            directory = self._one(transaction, _DIRECTORY, values, neutral=True)
            if directory is None:
                return None
            lifecycle = DatabaseManifestHandoffSupervisorControlDirectories._lifecycle(directory)
            if type(lifecycle) is not RetiredManifestHandoffSupervisorControlDirectory:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if lifecycle != decision.retired:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            latest = self._one(transaction, _LATEST_DECISION, values, neutral=True)
            sequence = 1 if latest is None else latest.sequence_number + 1
            if type(sequence) is not int or sequence < 1:
                raise ManifestHandoffRegistryUnavailable
            transaction.execute(text(
                "INSERT INTO manifest_handoff_supervisor_control_cleanup_decisions"
                " (decision_id,directory_id,sequence_number,policy_revision_id,"
                " disposition,decided_at)"
                " VALUES (:decision,:directory,:sequence,:policy,:disposition,:decided)"
            ), {**values, "sequence": sequence,
                "policy": _encode(decision.policy_revision_id),
                "disposition": decision.disposition.value,
                "decided": decision.decided_at})
            return decision
        return self._write(action)

    def resolve_control_directory_cleanup_decision(self, directory_id):
        if type(directory_id) is not ManifestHandoffSupervisorControlDirectoryId:
            raise ManifestHandoffRegistryUnavailable
        return self._read(lambda connection: self._resolved_decision(
            connection, {"directory": _encode(directory_id)}))

    def start_cleanup_attempt(self, request, decision):
        if (type(request) is not CleanupManifestHandoffSupervisorControlDirectory
                or type(decision) is not ManifestHandoffSupervisorControlDirectoryCleanupDecision):
            raise ManifestHandoffRegistryUnavailable

        def action(transaction):
            values = {"attempt": _encode(request.attempt_id),
                "directory": _encode(request.directory_id)}
            existing = self._one(transaction, _ATTEMPT, values, neutral=True)
            if existing is not None:
                self._attempt(existing)
                return self._retry_request(existing, request, decision)
            current = self._resolved_decision(transaction, values)
            if current is None:
                return None
            if (current != decision
                    or current.disposition is not ManifestHandoffSupervisorControlDirectoryCleanupDisposition.ELIGIBLE):
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            now = _utc(self._clock())
            if now < current.decided_at:
                raise ManifestHandoffRegistryUnavailable
            transaction.execute(text(
                "INSERT INTO manifest_handoff_supervisor_control_cleanup_attempts"
                " (attempt_id,directory_id,actor_user_id,decision_id,state,started_at,"
                " unknown_at,outcome,completed_at,reconciliation_outcome,reconciled_at,write_claimed_at)"
                " VALUES (:attempt,:directory,:actor,:decision,'started',:now,"
                " NULL,NULL,NULL,NULL,NULL,NULL)"
            ), {**values, "actor": _encode(request.actor_user_id),
                "decision": _encode(decision.decision_id), "now": now})
            return request
        return self._write(action)

    def record_cleanup_outcome_unknown(self, required):
        if type(required) is not ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired:
            raise ManifestHandoffRegistryUnavailable
        return self._transition(required.attempt_id, required.directory_id,
            expected="write_claimed", target="outcome_unknown", outcome=None,
            result=lambda row, now: required)

    def complete_cleanup_attempt(self, attempt_id, directory_id, outcome):
        if not all((
            type(attempt_id) is ManifestHandoffSupervisorControlDirectoryCleanupAttemptId,
            type(directory_id) is ManifestHandoffSupervisorControlDirectoryId,
            type(outcome) is ManifestHandoffSupervisorControlDirectoryCleanupOutcome,
        )):
            raise ManifestHandoffRegistryUnavailable
        if outcome is not ManifestHandoffSupervisorControlDirectoryCleanupOutcome.ALREADY_ABSENT:
            raise ManifestHandoffRegistryUnavailable
        return self._transition(attempt_id, directory_id,
            expected="started", target="completed", outcome=outcome.value,
            result=lambda row, now: CompletedManifestHandoffSupervisorControlDirectoryCleanup(
                attempt_id, directory_id, outcome, now))

    def persist_control_directory_cleanup_physical_outcome(self, outcome):
        if type(outcome) not in (
                RemovedManifestHandoffSupervisorControlDirectory,
                UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect):
            raise ManifestHandoffRegistryUnavailable
        values = {"attempt": _encode(outcome.attempt_id),
                  "directory": _encode(outcome.directory_id)}

        def action(transaction):
            row = self._one(transaction, _ATTEMPT, values, neutral=True)
            if row is None:
                return None
            if _decode(row.directory_id) != outcome.directory_id.value:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if row.state in ("completed", "outcome_unknown"):
                return self._physical_outcome_retry(row, outcome)
            if row.state != "write_claimed":
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            claimed = self._claimed(
                row, outcome.attempt_id, outcome.directory_id, _utc(row.started_at))
            if claimed.claim_id != outcome.claim_id:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if type(outcome) is RemovedManifestHandoffSupervisorControlDirectory:
                if outcome.removed_at < claimed.claimed_at:
                    raise ManifestHandoffRegistryUnavailable
                sql = " SET state='completed',outcome='removed',completed_at=:at"
                result = CompletedManifestHandoffSupervisorControlDirectoryCleanup(
                    outcome.attempt_id, outcome.directory_id,
                    ManifestHandoffSupervisorControlDirectoryCleanupOutcome.REMOVED,
                    outcome.removed_at)
                at = outcome.removed_at
            else:
                at = _utc(self._clock())
                if at < claimed.claimed_at:
                    raise ManifestHandoffRegistryUnavailable
                sql = " SET state='outcome_unknown',unknown_at=:at"
                result = ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired(
                    outcome.attempt_id, outcome.directory_id)
            changed = transaction.execute(text(
                "UPDATE manifest_handoff_supervisor_control_cleanup_attempts" + sql
                + " WHERE attempt_id=:attempt AND directory_id=:directory"
                " AND state='write_claimed' AND EXISTS (SELECT 1 FROM"
                " manifest_handoff_supervisor_control_cleanup_write_claims claim"
                " WHERE claim.attempt_id=:attempt AND claim.directory_id=:directory"
                " AND claim.claim_id=:claim)"
            ), {**values, "at": at, "claim": _encode(outcome.claim_id)})
            if changed.rowcount != 1:
                raise ManifestHandoffRegistryUnavailable
            return result

        return self._write(action)

    def record_cleanup_reconciliation(self, request, outcome):
        if not all((
            type(request) is ReconcileManifestHandoffSupervisorControlDirectoryCleanup,
            type(outcome) is ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome,
        )):
            raise ManifestHandoffRegistryUnavailable
        return self._transition(request.attempt_id, request.directory_id,
            expected="outcome_unknown", target="reconciled", outcome=outcome.value,
            result=lambda row, now: ReconciledManifestHandoffSupervisorControlDirectoryCleanup(
                request.attempt_id, request.directory_id, outcome, now))

    def resolve_cleanup_attempt(self, attempt_id):
        if type(attempt_id) is not ManifestHandoffSupervisorControlDirectoryCleanupAttemptId:
            raise ManifestHandoffRegistryUnavailable
        def action(connection):
            row = self._one(connection, _ATTEMPT, {"attempt": _encode(attempt_id)}, neutral=True)
            return None if row is None else self._attempt(row)
        return self._read(action)

    def _transition(self, attempt_id, directory_id, *, expected, target, outcome, result):
        values = {"attempt": _encode(attempt_id), "directory": _encode(directory_id)}
        def action(transaction):
            row = self._one(transaction, _ATTEMPT, values, neutral=True)
            if row is None:
                return None
            if _decode(row.directory_id) != directory_id.value:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if row.state == target:
                current = self._attempt(row)
                if target == "outcome_unknown":
                    return current
                current_outcome = row.outcome if target == "completed" else row.reconciliation_outcome
                return current if current_outcome == outcome else ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            if row.state != expected:
                return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
            now = _utc(self._clock())
            if now < _utc(row.started_at):
                raise ManifestHandoffRegistryUnavailable
            if expected == "write_claimed" and (
                    row.write_claimed_at is None or now < _utc(row.write_claimed_at)):
                raise ManifestHandoffRegistryUnavailable
            if expected == "write_claimed":
                self._claimed(row, attempt_id, directory_id, _utc(row.started_at))
            if target == "outcome_unknown":
                sql = " SET state='outcome_unknown',unknown_at=:now"
                parameters = {**values, "now": now}
            elif target == "completed":
                sql = " SET state='completed',outcome=:outcome,completed_at=:now"
                parameters = {**values, "outcome": outcome, "now": now}
            else:
                if row.unknown_at is None or now < _utc(row.unknown_at):
                    raise ManifestHandoffRegistryUnavailable
                sql = " SET state='reconciled',reconciliation_outcome=:outcome,reconciled_at=:now"
                parameters = {**values, "outcome": outcome, "now": now}
            transaction.execute(text(
                "UPDATE manifest_handoff_supervisor_control_cleanup_attempts" + sql
                + " WHERE attempt_id=:attempt AND directory_id=:directory AND state=:expected"
            ), {**parameters, "expected": expected})
            return result(row, now)
        return self._write(action)

    def _resolved_decision(self, connection, values):
        row = self._one(connection, _LATEST_DECISION, values, neutral=True)
        return None if row is None else self._decision(row)

    @staticmethod
    def _physical_outcome_retry(row, outcome):
        if (row.state == "completed"
                and row.outcome != ManifestHandoffSupervisorControlDirectoryCleanupOutcome.REMOVED.value):
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        attempt = ManifestHandoffSupervisorControlDirectoryCleanupAttemptId(
            _decode(row.attempt_id))
        directory = ManifestHandoffSupervisorControlDirectoryId(_decode(row.directory_id))
        claimed = DatabaseManifestHandoffSupervisorControlDirectoryCleanup._claimed(
            row, attempt, directory, _utc(row.started_at))
        if claimed.claim_id != outcome.claim_id:
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        current = DatabaseManifestHandoffSupervisorControlDirectoryCleanup._attempt(row)
        if type(outcome) is RemovedManifestHandoffSupervisorControlDirectory:
            if (type(current) is CompletedManifestHandoffSupervisorControlDirectoryCleanup
                    and current.outcome is ManifestHandoffSupervisorControlDirectoryCleanupOutcome.REMOVED
                    and current.completed_at == outcome.removed_at):
                return current
        elif type(current) is ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired:
            return current
        return ManifestHandoffSupervisorControlDirectoryCleanupConflict()

    @staticmethod
    def _decision(row):
        if type(row.sequence_number) is not int or row.sequence_number < 1:
            raise ManifestHandoffRegistryUnavailable
        retired = DatabaseManifestHandoffSupervisorControlDirectories._lifecycle(row)
        if type(retired) is not RetiredManifestHandoffSupervisorControlDirectory:
            raise ManifestHandoffRegistryUnavailable
        return ManifestHandoffSupervisorControlDirectoryCleanupDecision(
            retired,
            ManifestHandoffSupervisorControlDirectoryRetentionDecisionId(_decode(row.decision_id)),
            ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId(_decode(row.policy_revision_id)),
            ManifestHandoffSupervisorControlDirectoryCleanupDisposition(row.disposition),
            _utc(row.decided_at))

    @staticmethod
    def _retry_request(row, request, decision):
        if not all((
            _decode(row.directory_id) == request.directory_id.value,
            _decode(row.actor_user_id) == request.actor_user_id,
            _decode(row.decision_id) == decision.decision_id.value,
        )):
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        return request

    @staticmethod
    def _attempt(row):
        attempt = ManifestHandoffSupervisorControlDirectoryCleanupAttemptId(_decode(row.attempt_id))
        directory = ManifestHandoffSupervisorControlDirectoryId(_decode(row.directory_id))
        started_at = _utc(row.started_at)
        if started_at < _utc(row.decision_decided_at):
            raise ManifestHandoffRegistryUnavailable
        claim_fields = (row.claim_id, row.clearance_id, row.preflight_id,
                        row.prepared_at, row.claimed_at)
        if row.state == "started":
            if any(value is not None for value in (row.write_claimed_at, row.unknown_at, row.outcome,
                    row.completed_at, row.reconciliation_outcome, row.reconciled_at, *claim_fields)):
                raise ManifestHandoffRegistryUnavailable
            return CleanupManifestHandoffSupervisorControlDirectory(
                attempt, UserId(_decode(row.actor_user_id)), directory)
        if row.state == "write_claimed":
            if any(value is not None for value in (row.unknown_at, row.outcome,
                    row.completed_at, row.reconciliation_outcome, row.reconciled_at)):
                raise ManifestHandoffRegistryUnavailable
            return DatabaseManifestHandoffSupervisorControlDirectoryCleanup._claimed(
                row, attempt, directory, started_at)
        if row.state == "outcome_unknown":
            if (row.unknown_at is None or any(value is not None for value in (
                    row.outcome, row.completed_at, row.reconciliation_outcome,
                    row.reconciled_at))):
                raise ManifestHandoffRegistryUnavailable
            claimed = DatabaseManifestHandoffSupervisorControlDirectoryCleanup._claimed(
                row, attempt, directory, started_at)
            if _utc(row.unknown_at) < claimed.claimed_at:
                raise ManifestHandoffRegistryUnavailable
            return ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired(attempt, directory)
        if row.state == "completed":
            if (row.unknown_at is not None or row.completed_at is None
                    or row.reconciliation_outcome is not None or row.reconciled_at is not None):
                raise ManifestHandoffRegistryUnavailable
            completed_at = _utc(row.completed_at)
            if row.outcome == ManifestHandoffSupervisorControlDirectoryCleanupOutcome.REMOVED.value:
                lower = DatabaseManifestHandoffSupervisorControlDirectoryCleanup._claimed(
                    row, attempt, directory, started_at).claimed_at
            elif row.outcome == ManifestHandoffSupervisorControlDirectoryCleanupOutcome.ALREADY_ABSENT.value:
                if row.write_claimed_at is not None or any(value is not None for value in claim_fields):
                    raise ManifestHandoffRegistryUnavailable
                lower = started_at
            else:
                raise ManifestHandoffRegistryUnavailable
            if completed_at < lower:
                raise ManifestHandoffRegistryUnavailable
            return CompletedManifestHandoffSupervisorControlDirectoryCleanup(
                attempt, directory, ManifestHandoffSupervisorControlDirectoryCleanupOutcome(row.outcome),
                completed_at)
        if (row.state == "reconciled" and row.unknown_at is not None
                and row.outcome is None and row.completed_at is None
                and row.reconciliation_outcome is not None
                and row.reconciled_at is not None):
            claimed = DatabaseManifestHandoffSupervisorControlDirectoryCleanup._claimed(
                row, attempt, directory, started_at)
            unknown_at = _utc(row.unknown_at)
            if unknown_at < claimed.claimed_at or _utc(row.reconciled_at) < unknown_at:
                raise ManifestHandoffRegistryUnavailable
            return ReconciledManifestHandoffSupervisorControlDirectoryCleanup(
                attempt, directory,
                ManifestHandoffSupervisorControlDirectoryCleanupReconciliationOutcome(row.reconciliation_outcome),
                _utc(row.reconciled_at))
        raise ManifestHandoffRegistryUnavailable

    @staticmethod
    def _claimed(row, attempt, directory, started_at):
        if row.write_claimed_at is None or any(value is None for value in (
                row.claim_id, row.clearance_id, row.preflight_id, row.prepared_at, row.claimed_at)):
            raise ManifestHandoffRegistryUnavailable
        prepared_at = _utc(row.prepared_at)
        claimed_at = _utc(row.claimed_at)
        if prepared_at < started_at or claimed_at < prepared_at or claimed_at != _utc(row.write_claimed_at):
            raise ManifestHandoffRegistryUnavailable
        prepared = PreparedManifestHandoffSupervisorControlDirectoryCleanup(
            ManifestHandoffSupervisorControlDirectoryCleanupPreflightId(_decode(row.preflight_id)),
            attempt,
            directory,
            ManifestHandoffSupervisorControlDirectoryCleanupClearanceId(_decode(row.clearance_id)),
            prepared_at,
        )
        return ClaimedManifestHandoffSupervisorControlDirectoryCleanup(
            ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimId(_decode(row.claim_id)),
            prepared,
            claimed_at,
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
