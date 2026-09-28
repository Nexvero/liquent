"""Read current persistent supervisor control-directory cleanup clearances."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import ManifestHandoffRegistryScopeId
from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    RetiredManifestHandoffSupervisorControlDirectory,
)
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
from liquent_platform.identity.manifest_handoff_supervisor_journal import (
    ManifestHandoffRecoveryJournalView,
    ManifestHandoffSupervisorJournalState,
    ManifestHandoffWriterJournalView,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_MANAGEMENT = text(
    "SELECT revision.revision_id,revision.actor_user_id,revision.scope_id,"
    " revision.sequence_number,revision.status,revision.resolved_at"
    " FROM manifest_handoff_supervisor_cleanup_management_revisions revision"
    " JOIN identity_users actor ON actor.user_id=revision.actor_user_id"
    " JOIN manifest_handoff_registry_scopes scope ON scope.scope_id=revision.scope_id"
    " WHERE revision.actor_user_id=:actor AND revision.scope_id=:scope"
    " AND actor.status='active' AND scope.status='active'"
    " ORDER BY revision.sequence_number DESC LIMIT 1"
)
_TARGET = {
    kind: text(
        "SELECT revision_id,directory_id,sequence_number,disposition,decided_at"
        f" FROM manifest_handoff_supervisor_cleanup_{kind}_revisions"
        " WHERE directory_id=:directory ORDER BY sequence_number DESC LIMIT 1"
    ) for kind in ("hold", "recovery", "reference")
}
_ACTIVE_POLICY = text(
    "SELECT policy.revision_id FROM mh_supervisor_cleanup_retention_policy_active active"
    " JOIN mh_supervisor_cleanup_retention_policy_revisions policy"
    " ON policy.revision_id=active.revision_id AND policy.data_class=active.data_class"
    " WHERE active.data_class='supervisor_control_directory'"
)
_CLEARANCE = text(
    "SELECT clearance_id,attempt_id,directory_id,actor_user_id,scope_id,"
    " terminal_observation_id,decision_id,management_revision_id,"
    " hold_revision_id,recovery_revision_id,reference_revision_id,cleared_at"
    " FROM manifest_handoff_supervisor_cleanup_clearances WHERE attempt_id=:attempt"
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


class DatabaseManifestHandoffSupervisorControlDirectoryCleanupClearance:
    """Resolve current revision-bound clearance facts without granting them."""

    __slots__ = ("_engine", "_directories", "_decisions", "_writer", "_recovery")

    def __init__(self, engine: Engine, *, directory_lookup, decision_lookup,
                 writer_journal_lookup, recovery_journal_lookup) -> None:
        if not isinstance(engine, Engine):
            raise ManifestHandoffRegistryUnavailable
        self._engine = engine
        self._directories = directory_lookup
        self._decisions = decision_lookup
        self._writer = writer_journal_lookup
        self._recovery = recovery_journal_lookup

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffSupervisorControlDirectoryCleanupClearance()"

    def resolve_control_directory_cleanup_management(self, actor_user_id, scope_id):
        if (type(actor_user_id) is not str or not actor_user_id
                or type(scope_id) is not ManifestHandoffRegistryScopeId):
            raise ManifestHandoffRegistryUnavailable
        values = {"actor": _encode(actor_user_id), "scope": _encode(scope_id)}
        def action(connection):
            row = self._one(connection, _MANAGEMENT, values, neutral=True)
            if row is None:
                return None
            self._sequence(row)
            return ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority(
                ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId(
                    _decode(row.revision_id)),
                UserId(_decode(row.actor_user_id)),
                ManifestHandoffRegistryScopeId(_decode(row.scope_id)),
                ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus(row.status),
                _utc(row.resolved_at),
            )
        return self._read(action)

    def resolve_control_directory_cleanup_hold(self, directory_id):
        return self._target(directory_id, "hold")

    def resolve_control_directory_cleanup_recovery(self, directory_id):
        return self._target(directory_id, "recovery")

    def resolve_control_directory_cleanup_references(self, directory_id):
        return self._target(directory_id, "reference")

    def _target(self, directory_id, kind):
        if type(directory_id) is not ManifestHandoffSupervisorControlDirectoryId:
            raise ManifestHandoffRegistryUnavailable
        values = {"directory": _encode(directory_id)}
        def action(connection):
            row = self._one(connection, _TARGET[kind], values, neutral=True)
            if row is None:
                return None
            self._sequence(row)
            retired = self._directories.resolve_control_directory(directory_id)
            if type(retired) is not RetiredManifestHandoffSupervisorControlDirectory:
                raise ManifestHandoffRegistryUnavailable
            revision_types = {
                "hold": ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId,
                "recovery": ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId,
                "reference": ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId,
            }
            value_types = {
                "hold": ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision,
                "recovery": ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision,
                "reference": ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision,
            }
            return value_types[kind](
                revision_types[kind](_decode(row.revision_id)), retired,
                ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition(
                    row.disposition), _utc(row.decided_at))
        return self._read(action)

    def resolve_control_directory_cleanup_clearance(self, request):
        if type(request) is not CleanupManifestHandoffSupervisorControlDirectory:
            raise ManifestHandoffRegistryUnavailable
        row = self._read(lambda connection: self._one(
            connection, _CLEARANCE, {"attempt": _encode(request.attempt_id)}, neutral=True))
        if row is None:
            return None
        if (_decode(row.directory_id) != request.directory_id.value
                or _decode(row.actor_user_id) != request.actor_user_id):
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()

        retired = self._directories.resolve_control_directory(request.directory_id)
        decision = self._decisions.resolve_control_directory_cleanup_decision(
            request.directory_id)
        if (type(retired) is not RetiredManifestHandoffSupervisorControlDirectory
                or decision is None):
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        active_policy = self._read(lambda connection: self._one(
            connection, _ACTIVE_POLICY, {}, neutral=True
        ))
        if (active_policy is None
                or active_policy.revision_id != _encode(decision.policy_revision_id)):
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        scope_id = ManifestHandoffRegistryScopeId(_decode(row.scope_id))
        management = self.resolve_control_directory_cleanup_management(
            request.actor_user_id, scope_id)
        hold = self.resolve_control_directory_cleanup_hold(request.directory_id)
        recovery = self.resolve_control_directory_cleanup_recovery(request.directory_id)
        references = self.resolve_control_directory_cleanup_references(request.directory_id)
        journal = self._journal(retired)
        current = (management, hold, recovery, references)
        if any(value is None for value in current):
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        if not all((
            decision.disposition is ManifestHandoffSupervisorControlDirectoryCleanupDisposition.ELIGIBLE,
            management.status is ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus.ACTIVE,
            hold.disposition is ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition.CLEAR,
            recovery.disposition is ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition.CLEAR,
            references.disposition is ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition.CLEAR,
            _decode(row.decision_id) == decision.decision_id.value,
            _decode(row.management_revision_id) == management.revision_id.value,
            _decode(row.hold_revision_id) == hold.revision_id.value,
            _decode(row.recovery_revision_id) == recovery.revision_id.value,
            _decode(row.reference_revision_id) == references.revision_id.value,
            _decode(row.terminal_observation_id) == journal.terminal_observation_id.value,
        )):
            return ManifestHandoffSupervisorControlDirectoryCleanupConflict()
        try:
            return ClearedManifestHandoffSupervisorControlDirectoryCleanup(
                ManifestHandoffSupervisorControlDirectoryCleanupClearanceId(
                    _decode(row.clearance_id)), request, retired, scope_id, journal,
                decision, management, hold, recovery, references, _utc(row.cleared_at))
        except ValueError:
            raise ManifestHandoffRegistryUnavailable from None

    def _journal(self, retired):
        writer = self._writer(retired.handle_id)
        recovery = self._recovery(retired.handle_id)
        present = [value for value in (writer, recovery) if value is not None]
        if len(present) != 1 or type(present[0]) not in (
                ManifestHandoffWriterJournalView, ManifestHandoffRecoveryJournalView):
            raise ManifestHandoffRegistryUnavailable
        journal = present[0]
        if (journal.state is not ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED
                or journal.terminal_observation_id is None or journal.result is None):
            raise ManifestHandoffRegistryUnavailable
        return journal

    @staticmethod
    def _sequence(row):
        if type(row.sequence_number) is not int or row.sequence_number < 1:
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
