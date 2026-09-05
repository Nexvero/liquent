"""Atomic persistent supervisor cleanup attempt and clearance creation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import secrets

from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import ManifestHandoffRegistryScopeId
from liquent_platform.identity.manifest_handoff_supervisor_control_directory import RetiredManifestHandoffSupervisorControlDirectory
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    CleanupManifestHandoffSupervisorControlDirectory,
    ManifestHandoffSupervisorControlDirectoryCleanupConflict,
    ManifestHandoffSupervisorControlDirectoryCleanupDisposition,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_clearance import (
    ClearedManifestHandoffSupervisorControlDirectoryCleanup,
    ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition,
    ManifestHandoffSupervisorControlDirectoryCleanupClearanceId,
    ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId,
    ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority,
    ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId,
    ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus,
    ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId,
    ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision,
    ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId,
)
from liquent_platform.identity.manifest_handoff_supervisor_journal import ManifestHandoffSupervisorJournalState
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_control_directories import DatabaseManifestHandoffSupervisorControlDirectories
from liquent_platform.persistence.manifest_handoff_supervisor_control_directory_cleanup import DatabaseManifestHandoffSupervisorControlDirectoryCleanup
from liquent_platform.persistence.manifest_handoff_supervisor_journal import DatabaseManifestHandoffSupervisorJournal


_DIRECTORY = text("SELECT directory_id,handle_id,leaf,state,reserved_at,activated_at,retired_at"
    " FROM manifest_handoff_supervisor_control_directories WHERE directory_id=:directory")
_JOB = text("SELECT * FROM manifest_handoff_supervisor_journal_jobs WHERE handle_id=:handle")
_TRANSITIONS = text("SELECT * FROM manifest_handoff_supervisor_journal_transitions"
    " WHERE handle_id=:handle ORDER BY sequence_number")
_DECISION = text("SELECT decision.decision_id,decision.directory_id,decision.sequence_number,"
    " decision.policy_revision_id,decision.disposition,decision.decided_at,directory.handle_id,"
    " directory.leaf,directory.state,directory.reserved_at,directory.activated_at,directory.retired_at"
    " FROM manifest_handoff_supervisor_control_cleanup_decisions decision"
    " JOIN manifest_handoff_supervisor_control_directories directory ON directory.directory_id=decision.directory_id"
    " WHERE decision.directory_id=:directory ORDER BY decision.sequence_number DESC LIMIT 1")
_MANAGEMENT = text("SELECT revision_id,actor_user_id,scope_id,sequence_number,status,resolved_at"
    " FROM manifest_handoff_supervisor_cleanup_management_revisions"
    " WHERE actor_user_id=:actor AND scope_id=:scope ORDER BY sequence_number DESC LIMIT 1")
_ATTEMPT = text("SELECT * FROM manifest_handoff_supervisor_control_cleanup_attempts WHERE attempt_id=:attempt")
_CLEARANCE = text("SELECT * FROM manifest_handoff_supervisor_cleanup_clearances WHERE attempt_id=:attempt")
_ACTIVE_POLICY = text("SELECT policy.revision_id FROM mh_supervisor_cleanup_retention_policy_active active"
    " JOIN mh_supervisor_cleanup_retention_policy_revisions policy"
    " ON policy.revision_id=active.revision_id AND policy.data_class=active.data_class"
    " WHERE active.data_class='supervisor_control_directory'")


def _target_query(kind):
    return text(f"SELECT revision_id,directory_id,sequence_number,disposition,decided_at"
        f" FROM manifest_handoff_supervisor_cleanup_{kind}_revisions"
        " WHERE directory_id=:directory ORDER BY sequence_number DESC LIMIT 1")


def _encode(value):
    raw = value.value if hasattr(value, "value") else value
    if type(raw) is not str or not raw: raise ManifestHandoffRegistryUnavailable
    return raw.encode("utf-8")


def _decode(value):
    try:
        if not isinstance(value, (bytes, bytearray, memoryview)) or not value: raise ManifestHandoffRegistryUnavailable
        result = bytes(value).decode("utf-8")
    except UnicodeError: raise ManifestHandoffRegistryUnavailable from None
    if not result: raise ManifestHandoffRegistryUnavailable
    return result


def _utc(value):
    if type(value) is str:
        try: value = datetime.fromisoformat(value)
        except ValueError: raise ManifestHandoffRegistryUnavailable from None
    if type(value) is not datetime: raise ManifestHandoffRegistryUnavailable
    value = value.replace(tzinfo=value.tzinfo or timezone.utc)
    if value.utcoffset() != timedelta(0): raise ManifestHandoffRegistryUnavailable
    return value


class DatabaseManifestHandoffSupervisorCleanupClearanceCreation:
    """Create one started attempt and its current positive clearance atomically."""

    __slots__ = ("_engine", "_clock", "_clearance")

    def __init__(self, engine: Engine, *, clock: Callable[[], datetime] | None = None,
                 clearance_id_generator: Callable[[], str] | None = None):
        if (not isinstance(engine, Engine) or (clock is not None and not callable(clock))
                or (clearance_id_generator is not None and not callable(clearance_id_generator))):
            raise ManifestHandoffRegistryUnavailable
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._clearance = clearance_id_generator or (lambda: secrets.token_hex(32))

    def __repr__(self): return "DatabaseManifestHandoffSupervisorCleanupClearanceCreation()"

    def create_control_directory_cleanup_clearance(self, principal, request):
        if (type(principal) is not SessionPrincipal
                or type(request) is not CleanupManifestHandoffSupervisorControlDirectory):
            raise ManifestHandoffRegistryUnavailable
        if principal.user_id != request.actor_user_id:
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        values = {"attempt": _encode(request.attempt_id), "actor": _encode(request.actor_user_id),
            "directory": _encode(request.directory_id)}
        def action(connection):
            attempt = self._one(connection, _ATTEMPT, values, True)
            clearance = self._one(connection, _CLEARANCE, values, True)
            if attempt is not None or clearance is not None:
                if attempt is None or clearance is None:
                    return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
                return self._retry(connection, request, values, attempt, clearance)
            facts = self._facts(connection, request, values)
            if facts is None: return None
            retired, scope, journal, decision, management, hold, recovery, references = facts
            now = _utc(self._clock())
            lower = max(retired.retired_at, decision.decided_at, management.resolved_at,
                hold.decided_at, recovery.decided_at, references.decided_at, journal.observed_at)
            if now < lower: raise ManifestHandoffRegistryUnavailable
            clearance_id = self._new_clearance_id()
            connection.execute(text("INSERT INTO manifest_handoff_supervisor_control_cleanup_attempts"
                " (attempt_id,directory_id,actor_user_id,decision_id,state,started_at,unknown_at,outcome,"
                " completed_at,reconciliation_outcome,reconciled_at,write_claimed_at) VALUES"
                " (:attempt,:directory,:actor,:decision,'started',:now,NULL,NULL,NULL,NULL,NULL,NULL)"),
                {**values, "decision": _encode(decision.decision_id), "now": now})
            connection.execute(text("INSERT INTO manifest_handoff_supervisor_cleanup_clearances"
                " (clearance_id,attempt_id,directory_id,actor_user_id,scope_id,terminal_observation_id,"
                " decision_id,management_revision_id,hold_revision_id,recovery_revision_id,reference_revision_id,cleared_at)"
                " VALUES (:clearance,:attempt,:directory,:actor,:scope,:terminal,:decision,:management,"
                " :hold,:recovery,:reference,:now)"), {**values, "clearance": clearance_id,
                "scope": _encode(scope), "terminal": _encode(journal.terminal_observation_id),
                "decision": _encode(decision.decision_id), "management": _encode(management.revision_id),
                "hold": _encode(hold.revision_id), "recovery": _encode(recovery.revision_id),
                "reference": _encode(references.revision_id), "now": now})
            return ClearedManifestHandoffSupervisorControlDirectoryCleanup(
                ManifestHandoffSupervisorControlDirectoryCleanupClearanceId(_decode(clearance_id)),
                request, retired, scope, journal, decision, management, hold, recovery, references, now)
        return self._write(action)

    def _retry(self, connection, request, values, attempt, clearance):
        if not all((attempt.directory_id == values["directory"], attempt.actor_user_id == values["actor"],
                attempt.state == "started", clearance.directory_id == values["directory"],
                clearance.actor_user_id == values["actor"], clearance.attempt_id == values["attempt"])):
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        facts = self._facts(connection, request, values)
        if facts is None: return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        retired, scope, journal, decision, management, hold, recovery, references = facts
        if not all((attempt.decision_id == _encode(decision.decision_id),
                clearance.scope_id == _encode(scope),
                clearance.terminal_observation_id == _encode(journal.terminal_observation_id),
                clearance.decision_id == _encode(decision.decision_id),
                clearance.management_revision_id == _encode(management.revision_id),
                clearance.hold_revision_id == _encode(hold.revision_id),
                clearance.recovery_revision_id == _encode(recovery.revision_id),
                clearance.reference_revision_id == _encode(references.revision_id))):
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        return ClearedManifestHandoffSupervisorControlDirectoryCleanup(
            ManifestHandoffSupervisorControlDirectoryCleanupClearanceId(_decode(clearance.clearance_id)),
            request, retired, scope, journal, decision, management, hold, recovery, references,
            _utc(clearance.cleared_at))

    def _facts(self, connection, request, values):
        directory = self._one(connection, _DIRECTORY, values, True)
        if directory is None: return None
        retired = DatabaseManifestHandoffSupervisorControlDirectories._lifecycle(directory)
        if type(retired) is not RetiredManifestHandoffSupervisorControlDirectory: return None
        job = self._one(connection, _JOB, {"handle": _encode(retired.handle_id)}, True)
        if job is None: raise ManifestHandoffRegistryUnavailable
        history = connection.execute(_TRANSITIONS, {"handle": _encode(retired.handle_id)}).all()
        journal = DatabaseManifestHandoffSupervisorJournal.reconstruct_view(job, history)
        if (journal.state is not ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED
                or journal.terminal_observation_id is None or journal.result is None):
            raise ManifestHandoffRegistryUnavailable
        scope = journal.registration.process_request.binding.scope_id
        if not self._active_foundations(connection, values["actor"], _encode(scope)): return None
        decision_row = self._one(connection, _DECISION, values, True)
        management_row = self._one(connection, _MANAGEMENT,
            {"actor": values["actor"], "scope": _encode(scope)}, True)
        target_rows = [self._one(connection, _target_query(kind), values, True)
            for kind in ("hold", "recovery", "reference")]
        if decision_row is None or management_row is None or any(row is None for row in target_rows): return None
        decision = DatabaseManifestHandoffSupervisorControlDirectoryCleanup._decision(decision_row)
        if decision.disposition is not ManifestHandoffSupervisorControlDirectoryCleanupDisposition.ELIGIBLE:
            return None
        active_policy = self._one(connection, _ACTIVE_POLICY, {}, True)
        if (active_policy is None
                or active_policy.revision_id != _encode(decision.policy_revision_id)):
            return None
        if type(management_row.sequence_number) is not int or management_row.sequence_number < 1:
            raise ManifestHandoffRegistryUnavailable
        management = ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority(
            ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId(_decode(management_row.revision_id)),
            UserId(_decode(management_row.actor_user_id)), ManifestHandoffRegistryScopeId(_decode(management_row.scope_id)),
            ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus(management_row.status),
            _utc(management_row.resolved_at))
        if management.status is not ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus.ACTIVE: return None
        decisions = []
        types = ((ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId,
                  ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision),
                 (ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId,
                  ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision),
                 (ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId,
                  ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision))
        for row, (revision_type, decision_type) in zip(target_rows, types):
            if type(row.sequence_number) is not int or row.sequence_number < 1: raise ManifestHandoffRegistryUnavailable
            value = decision_type(revision_type(_decode(row.revision_id)), retired,
                ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition(row.disposition),
                _utc(row.decided_at))
            if value.disposition is not ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition.CLEAR:
                return None
            decisions.append(value)
        return retired, scope, journal, decision, management, *decisions

    @staticmethod
    def _active_foundations(connection, actor, scope):
        return connection.execute(text("SELECT 1 FROM identity_users users JOIN manifest_handoff_registry_scopes scopes"
            " ON scopes.scope_id=:scope WHERE users.user_id=:actor AND users.status='active' AND scopes.status='active'"),
            {"actor": actor, "scope": scope}).first() is not None

    def _new_clearance_id(self):
        try: return _encode(ManifestHandoffSupervisorControlDirectoryCleanupClearanceId(self._clearance()))
        except (TypeError, ValueError): raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _one(connection, query, values, neutral=False):
        rows = connection.execute(query, values).all()
        if not rows:
            if neutral: return None
            raise ManifestHandoffRegistryUnavailable
        if len(rows) != 1: raise ManifestHandoffRegistryUnavailable
        return rows[0]

    def _write(self, action):
        try:
            with self._engine.begin() as connection:
                if connection.dialect.name == "postgresql":
                    connection.execute(text("LOCK TABLE identity_users,manifest_handoff_registry_scopes,"
                        " manifest_handoff_supervisor_control_directories,manifest_handoff_supervisor_journal_jobs,"
                        " manifest_handoff_supervisor_journal_transitions,manifest_handoff_supervisor_control_cleanup_decisions,"
                        " mh_supervisor_cleanup_retention_policy_revisions,mh_supervisor_cleanup_retention_policy_active,"
                        " manifest_handoff_supervisor_cleanup_management_revisions,manifest_handoff_supervisor_cleanup_hold_revisions,"
                        " manifest_handoff_supervisor_cleanup_recovery_revisions,manifest_handoff_supervisor_cleanup_reference_revisions,"
                        " manifest_handoff_supervisor_control_cleanup_attempts,manifest_handoff_supervisor_cleanup_clearances"
                        " IN SHARE ROW EXCLUSIVE MODE"))
                elif connection.dialect.name != "sqlite": raise ManifestHandoffRegistryUnavailable
                return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None: raise
        except Exception: pass
        raise ManifestHandoffRegistryUnavailable
