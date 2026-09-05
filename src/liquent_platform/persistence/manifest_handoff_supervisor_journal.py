"""Strict persistent state machine for the internal supervisor journal."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import Engine, text

from liquent_platform.identity.manifest_handoff import (
    ManifestHandoffExecutionClaimId, ManifestHandoffExecutionOwnerId,
    ManifestHandoffFacts, ManifestHandoffName, ManifestHandoffRecoveryClaimId,
    ManifestHandoffRecoveryOwnerId, ManifestHandoffRegistryScopeId,
    ManifestHandoffScopeBinding,
)
from liquent_platform.identity.manifest_handoff_supervisor import (
    CompletedManifestHandoffRecoveryProcess, CompletedManifestHandoffWriterProcess,
    ManifestHandoffRecoveryProcessKind, ManifestHandoffRecoverySupervisorRequest,
    ManifestHandoffSupervisorHandleId, ManifestHandoffWriterProcessKind,
    ManifestHandoffWriterSupervisorRequest,
)
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId, ManifestHandoffSupervisorPrepareId,
    ManifestHandoffSupervisorReleaseId, ManifestHandoffSupervisorTerminateId,
    ManifestHandoffSupervisorTerminalObservationId,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    CommitManifestHandoffSupervisorGateRelease, CommitManifestHandoffSupervisorLaunch,
    ManifestHandoffRecoveryJournalView, ManifestHandoffSupervisorGatedObservationId,
    ManifestHandoffSupervisorJournalConflict, ManifestHandoffSupervisorJournalState,
    ManifestHandoffSupervisorLaunchCommitId,
    ManifestHandoffSupervisorRunningObservationId, ManifestHandoffWriterJournalView,
    RecordManifestHandoffRecoveryJournalTerminal, RecordManifestHandoffSupervisorGated,
    RecordManifestHandoffSupervisorRunning, RecordManifestHandoffWriterJournalTerminal,
    RegisterManifestHandoffRecoveryJournalJob, RegisterManifestHandoffWriterJournalJob,
    RequestManifestHandoffSupervisorTermination,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_LOCK = text(
    "LOCK TABLE manifest_handoff_supervisor_journal_jobs,"
    " manifest_handoff_supervisor_journal_transitions IN SHARE ROW EXCLUSIVE MODE"
)
_JOB_BY_IDENTITIES = text(
    "SELECT * FROM manifest_handoff_supervisor_journal_jobs"
    " WHERE handle_id=:handle OR prepare_id=:prepare OR launch_commit_id=:launch"
)
_JOB = text(
    "SELECT * FROM manifest_handoff_supervisor_journal_jobs WHERE handle_id=:handle"
)
_TRANSITIONS = text(
    "SELECT * FROM manifest_handoff_supervisor_journal_transitions"
    " WHERE handle_id=:handle ORDER BY sequence_number"
)
_TRANSITION_ID = text(
    "SELECT * FROM manifest_handoff_supervisor_journal_transitions"
    " WHERE transition_id=:transition"
)
_TRANSITION_KIND = text(
    "SELECT transition_id FROM manifest_handoff_supervisor_journal_transitions"
    " WHERE handle_id=:handle AND kind=:kind"
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


_STATE = {
    "launch_committed": ManifestHandoffSupervisorJournalState.LAUNCH_COMMITTED,
    "prepared_gated": ManifestHandoffSupervisorJournalState.PREPARED_GATED,
    "release_committed": ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED,
    "running": ManifestHandoffSupervisorJournalState.RUNNING,
    "termination_requested": ManifestHandoffSupervisorJournalState.TERMINATION_REQUESTED,
    "terminal_observed": ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED,
}


class DatabaseManifestHandoffSupervisorJournal:
    """Persist one backend's closed writer and recovery journal histories."""

    __slots__ = ("_engine", "_backend", "_clock")

    def __init__(self, engine: Engine, *, backend_instance_id: ManifestHandoffSupervisorBackendInstanceId, clock: Callable[[], datetime] | None = None) -> None:
        if type(backend_instance_id) is not ManifestHandoffSupervisorBackendInstanceId:
            raise ValueError("manifest handoff supervisor journal backend is invalid")
        self._engine = engine
        self._backend = backend_instance_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffSupervisorJournal()"

    def register_writer(self, request):
        return self._register(request, RegisterManifestHandoffWriterJournalJob, "writer")

    def register_recovery(self, request):
        return self._register(request, RegisterManifestHandoffRecoveryJournalJob, "recovery")

    def _register(self, request, request_type, capability):
        if type(request) is not request_type or request.backend_instance_id != self._backend:
            raise ManifestHandoffRegistryUnavailable
        process = request.process_request
        values = {
            "handle": _encode(request.handle_id), "backend": _encode(self._backend),
            "prepare": _encode(request.prepare_id), "launch": _encode(request.launch_commit_id),
            "capability": capability, "claim": _encode(process.claim_id),
            "owner": _encode(process.owner_id), "scope": _encode(process.binding.scope_id),
            "source": str(process.binding.source_root), "target": str(process.binding.target_root),
            "name": process.handoff_name.value,
        }
        def action(transaction):
            rows = transaction.execute(_JOB_BY_IDENTITIES, values).all()
            if rows:
                if len(rows) != 1 or not self._same_job(rows[0], values):
                    return ManifestHandoffSupervisorJournalConflict()
                return self._view(rows[0], transaction.execute(_TRANSITIONS, values).all())
            now = _utc(self._clock())
            execution = values["claim"] if capability == "writer" else None
            recovery = values["claim"] if capability == "recovery" else None
            transaction.execute(text(
                "INSERT INTO manifest_handoff_supervisor_journal_jobs"
                " (handle_id,backend_instance_id,prepare_id,launch_commit_id,capability,"
                " execution_claim_id,recovery_claim_id,owner_id,scope_id,source_root,"
                " target_root,handoff_name,registered_at) VALUES"
                " (:handle,:backend,:prepare,:launch,:capability,:execution,:recovery,"
                " :owner,:scope,:source,:target,:name,:now)"
            ), {**values, "execution": execution, "recovery": recovery, "now": now})
            return self._registration_view(request, capability, now)
        return self._write(action)

    @staticmethod
    def _same_job(row, values):
        claim = row.execution_claim_id if values["capability"] == "writer" else row.recovery_claim_id
        other = row.recovery_claim_id if values["capability"] == "writer" else row.execution_claim_id
        return all((row.handle_id == values["handle"], row.backend_instance_id == values["backend"],
            row.prepare_id == values["prepare"], row.launch_commit_id == values["launch"],
            row.capability == values["capability"], claim == values["claim"], other is None,
            row.owner_id == values["owner"], row.scope_id == values["scope"],
            row.source_root == values["source"], row.target_root == values["target"],
            row.handoff_name == values["name"]))

    @staticmethod
    def _registration_view(request, capability, now):
        view = ManifestHandoffWriterJournalView if capability == "writer" else ManifestHandoffRecoveryJournalView
        return view(request, ManifestHandoffSupervisorJournalState.PREPARE_REGISTERED, now)

    def commit_writer_launch(self, request): return self._transition(request, CommitManifestHandoffSupervisorLaunch, "writer", "launch_committed")
    def record_writer_gated(self, request): return self._transition(request, RecordManifestHandoffSupervisorGated, "writer", "prepared_gated")
    def commit_writer_release(self, request): return self._transition(request, CommitManifestHandoffSupervisorGateRelease, "writer", "release_committed")
    def record_writer_running(self, request): return self._transition(request, RecordManifestHandoffSupervisorRunning, "writer", "running")
    def request_writer_termination(self, request): return self._transition(request, RequestManifestHandoffSupervisorTermination, "writer", "termination_requested")
    def record_writer_terminal(self, request): return self._transition(request, RecordManifestHandoffWriterJournalTerminal, "writer", "terminal_observed")
    def commit_recovery_launch(self, request): return self._transition(request, CommitManifestHandoffSupervisorLaunch, "recovery", "launch_committed")
    def record_recovery_gated(self, request): return self._transition(request, RecordManifestHandoffSupervisorGated, "recovery", "prepared_gated")
    def commit_recovery_release(self, request): return self._transition(request, CommitManifestHandoffSupervisorGateRelease, "recovery", "release_committed")
    def record_recovery_running(self, request): return self._transition(request, RecordManifestHandoffSupervisorRunning, "recovery", "running")
    def request_recovery_termination(self, request): return self._transition(request, RequestManifestHandoffSupervisorTermination, "recovery", "termination_requested")
    def record_recovery_terminal(self, request): return self._transition(request, RecordManifestHandoffRecoveryJournalTerminal, "recovery", "terminal_observed")

    def _transition(self, request, request_type, capability, kind):
        if type(request) is not request_type:
            raise ManifestHandoffRegistryUnavailable
        identity = self._transition_identity(request, kind)
        values = {"transition": _encode(identity), "handle": _encode(request.handle_id), "kind": kind}
        def action(transaction):
            existing = transaction.execute(_TRANSITION_ID, values).all()
            if existing:
                if len(existing) != 1 or existing[0].handle_id != values["handle"] or existing[0].kind != kind:
                    return ManifestHandoffSupervisorJournalConflict()
                job = self._one_job(transaction, values, capability, neutral=True)
                if job is None:
                    return None
                return self._view(job, transaction.execute(_TRANSITIONS, values).all())
            job = self._one_job(transaction, values, capability, neutral=True)
            if job is None:
                return None
            history = transaction.execute(_TRANSITIONS, values).all()
            current = self._validate_history(job, history)
            if not self._allowed(current, kind):
                return ManifestHandoffSupervisorJournalConflict()
            if kind == "launch_committed" and job.launch_commit_id != values["transition"]:
                return ManifestHandoffSupervisorJournalConflict()
            if transaction.execute(_TRANSITION_KIND, values).first() is not None:
                return ManifestHandoffSupervisorJournalConflict()
            now = (
                _utc(request.result.ended_at)
                if kind == "terminal_observed"
                else _utc(self._clock())
            )
            outcome = filename = digest = count = None
            if kind == "terminal_observed":
                result = request.result
                outcome = result.kind.value
                filename = result.filename
                if result.facts is not None:
                    digest, count = result.facts.manifest_sha256, result.facts.file_count
            transaction.execute(text(
                "INSERT INTO manifest_handoff_supervisor_journal_transitions"
                " (transition_id,handle_id,capability,sequence_number,kind,outcome_kind,"
                " filename,manifest_sha256,file_count,observed_at) VALUES"
                " (:transition,:handle,:capability,:sequence,:kind,:outcome,:filename,"
                " :digest,:count,:now)"
            ), {**values, "capability": capability, "sequence": len(history)+1,
                "outcome": outcome, "filename": filename, "digest": digest,
                "count": count, "now": now})
            return self._view(job, transaction.execute(_TRANSITIONS, values).all())
        return self._write(action)

    @staticmethod
    def _transition_identity(request, kind):
        attribute = {"launch_committed": "launch_commit_id", "prepared_gated": "observation_id",
            "release_committed": "release_id", "running": "observation_id",
            "termination_requested": "terminate_id",
            "terminal_observed": "terminal_observation_id"}[kind]
        return getattr(request, attribute)

    @staticmethod
    def _allowed(current, kind):
        allowed = {
            "launch_committed": {ManifestHandoffSupervisorJournalState.PREPARE_REGISTERED},
            "prepared_gated": {ManifestHandoffSupervisorJournalState.LAUNCH_COMMITTED},
            "release_committed": {ManifestHandoffSupervisorJournalState.PREPARED_GATED},
            "running": {ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED},
            "termination_requested": {ManifestHandoffSupervisorJournalState.LAUNCH_COMMITTED, ManifestHandoffSupervisorJournalState.PREPARED_GATED, ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED, ManifestHandoffSupervisorJournalState.RUNNING},
            "terminal_observed": {ManifestHandoffSupervisorJournalState.LAUNCH_COMMITTED, ManifestHandoffSupervisorJournalState.PREPARED_GATED, ManifestHandoffSupervisorJournalState.RELEASE_COMMITTED, ManifestHandoffSupervisorJournalState.RUNNING, ManifestHandoffSupervisorJournalState.TERMINATION_REQUESTED},
        }
        return current in allowed[kind]

    def inspect_writer_journal(self, handle_id): return self._inspect(handle_id, "writer")
    def inspect_recovery_journal(self, handle_id): return self._inspect(handle_id, "recovery")

    def _inspect(self, handle_id, capability):
        if type(handle_id) is not ManifestHandoffSupervisorHandleId:
            raise ManifestHandoffRegistryUnavailable
        values = {"handle": _encode(handle_id)}
        def action(connection):
            job = self._one_job(connection, values, capability, neutral=True)
            if job is None:
                return None
            return self._view(job, connection.execute(_TRANSITIONS, values).all())
        return self._read(action)

    @staticmethod
    def _one_job(connection, values, capability, neutral=False):
        rows = connection.execute(_JOB, values).all()
        if not rows:
            if neutral: return None
            raise ManifestHandoffRegistryUnavailable
        if len(rows) != 1:
            raise ManifestHandoffRegistryUnavailable
        if rows[0].capability != capability:
            return None
        return rows[0]

    @classmethod
    def reconstruct_view(cls, job, history):
        """Reconstruct one validated view from rows already read transactionally."""
        return cls._view(job, history)

    @classmethod
    def _view(cls, job, history):
        state = cls._validate_history(job, history)
        registration = cls._registration(job)
        release = terminate = terminal = result = None
        observed = _utc(job.registered_at)
        for row in history:
            observed = _utc(row.observed_at)
            if row.kind == "release_committed": release = ManifestHandoffSupervisorReleaseId(_decode(row.transition_id))
            elif row.kind == "termination_requested": terminate = ManifestHandoffSupervisorTerminateId(_decode(row.transition_id))
            elif row.kind == "terminal_observed":
                terminal = ManifestHandoffSupervisorTerminalObservationId(_decode(row.transition_id))
                result = cls._terminal_result(job, row, observed)
        view = ManifestHandoffWriterJournalView if job.capability == "writer" else ManifestHandoffRecoveryJournalView
        return view(registration, state, observed, release, terminate, terminal, result)

    @staticmethod
    def _registration(row):
        binding = ManifestHandoffScopeBinding(ManifestHandoffRegistryScopeId(_decode(row.scope_id)), Path(row.source_root), Path(row.target_root))
        name = ManifestHandoffName(row.handoff_name)
        if row.capability == "writer" and row.execution_claim_id is not None and row.recovery_claim_id is None:
            request = ManifestHandoffWriterSupervisorRequest(ManifestHandoffExecutionClaimId(_decode(row.execution_claim_id)), ManifestHandoffExecutionOwnerId(_decode(row.owner_id)), binding, name)
            cls = RegisterManifestHandoffWriterJournalJob
        elif row.capability == "recovery" and row.execution_claim_id is None and row.recovery_claim_id is not None:
            request = ManifestHandoffRecoverySupervisorRequest(ManifestHandoffRecoveryClaimId(_decode(row.recovery_claim_id)), ManifestHandoffRecoveryOwnerId(_decode(row.owner_id)), binding, name)
            cls = RegisterManifestHandoffRecoveryJournalJob
        else: raise ManifestHandoffRegistryUnavailable
        return cls(ManifestHandoffSupervisorBackendInstanceId(_decode(row.backend_instance_id)), ManifestHandoffSupervisorPrepareId(_decode(row.prepare_id)), ManifestHandoffSupervisorLaunchCommitId(_decode(row.launch_commit_id)), ManifestHandoffSupervisorHandleId(_decode(row.handle_id)), request)

    @classmethod
    def _validate_history(cls, job, history):
        current = ManifestHandoffSupervisorJournalState.PREPARE_REGISTERED
        for index, row in enumerate(history, 1):
            if row.sequence_number != index or row.capability != job.capability or row.kind not in _STATE or not cls._allowed(current, row.kind):
                raise ManifestHandoffRegistryUnavailable
            current = _STATE[row.kind]
        return current

    @staticmethod
    def _terminal_result(job, row, ended_at):
        facts = None if row.manifest_sha256 is None else ManifestHandoffFacts(row.manifest_sha256, row.file_count)
        handle = ManifestHandoffSupervisorHandleId(_decode(job.handle_id))
        if job.capability == "writer":
            return CompletedManifestHandoffWriterProcess(handle, ManifestHandoffExecutionClaimId(_decode(job.execution_claim_id)), ManifestHandoffExecutionOwnerId(_decode(job.owner_id)), ManifestHandoffWriterProcessKind(row.outcome_kind), ended_at, row.filename, facts)
        return CompletedManifestHandoffRecoveryProcess(handle, ManifestHandoffRecoveryClaimId(_decode(job.recovery_claim_id)), ManifestHandoffRecoveryOwnerId(_decode(job.owner_id)), ManifestHandoffRecoveryProcessKind(row.outcome_kind), ended_at, row.filename, facts)

    def _write(self, action):
        try:
            with self._engine.begin() as connection:
                self._dialect(connection, True); return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None: raise
        except Exception: pass
        raise ManifestHandoffRegistryUnavailable

    def _read(self, action):
        try:
            with self._engine.connect() as connection:
                self._dialect(connection, False); return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None: raise
        except Exception: pass
        raise ManifestHandoffRegistryUnavailable

    @staticmethod
    def _dialect(connection, lock):
        if connection.dialect.name == "postgresql":
            if lock: connection.execute(_LOCK)
        elif connection.dialect.name != "sqlite": raise ManifestHandoffRegistryUnavailable
