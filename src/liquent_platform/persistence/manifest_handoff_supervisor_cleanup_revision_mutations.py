"""Authorized append-only cleanup source revision mutations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets

from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.manifest_handoff import ManifestHandoffRegistryScopeId
from liquent_platform.identity.manifest_handoff_supervisor_control_directory import RetiredManifestHandoffSupervisorControlDirectory
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_clearance import (
    ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition,
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
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup_clearance_mutation import (
    ChangeManifestHandoffSupervisorControlDirectoryCleanupHold,
    ChangeManifestHandoffSupervisorControlDirectoryCleanupManagement,
    ChangeManifestHandoffSupervisorControlDirectoryCleanupRecovery,
    ChangeManifestHandoffSupervisorControlDirectoryCleanupReference,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupHoldChange,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupManagementChange,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupRecoveryChange,
    CommittedManifestHandoffSupervisorControlDirectoryCleanupReferenceChange,
    ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.persistence.manifest_handoff_supervisor_control_directories import DatabaseManifestHandoffSupervisorControlDirectories


@dataclass(frozen=True)
class _Source:
    kind: str
    command_type: type
    revision_type: type
    decision_type: type
    result_type: type

    @property
    def revisions(self): return f"manifest_handoff_supervisor_cleanup_{self.kind}_revisions"
    @property
    def changes(self): return f"manifest_handoff_supervisor_cleanup_{self.kind}_changes"
    @property
    def authorizations(self): return f"mh_supervisor_cleanup_{self.kind}_change_authorizations"
    @property
    def authority(self): return f"mh_supervisor_cleanup_{self.kind}_authority"


_SOURCES = {
    "hold": _Source("hold", ChangeManifestHandoffSupervisorControlDirectoryCleanupHold,
        ManifestHandoffSupervisorControlDirectoryCleanupHoldRevisionId,
        ManifestHandoffSupervisorControlDirectoryCleanupHoldDecision,
        CommittedManifestHandoffSupervisorControlDirectoryCleanupHoldChange),
    "recovery": _Source("recovery", ChangeManifestHandoffSupervisorControlDirectoryCleanupRecovery,
        ManifestHandoffSupervisorControlDirectoryCleanupRecoveryRevisionId,
        ManifestHandoffSupervisorControlDirectoryCleanupRecoveryDecision,
        CommittedManifestHandoffSupervisorControlDirectoryCleanupRecoveryChange),
    "reference": _Source("reference", ChangeManifestHandoffSupervisorControlDirectoryCleanupReference,
        ManifestHandoffSupervisorControlDirectoryCleanupReferenceRevisionId,
        ManifestHandoffSupervisorControlDirectoryCleanupReferenceDecision,
        CommittedManifestHandoffSupervisorControlDirectoryCleanupReferenceChange),
}


def _encode(value: object) -> bytes:
    raw = value.value if hasattr(value, "value") else value
    if type(raw) is not str or not raw: raise ManifestHandoffRegistryUnavailable
    return raw.encode("utf-8")


def _decode(value: object) -> str:
    try:
        if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
            raise ManifestHandoffRegistryUnavailable
        result = bytes(value).decode("utf-8")
    except UnicodeError:
        raise ManifestHandoffRegistryUnavailable from None
    if not result: raise ManifestHandoffRegistryUnavailable
    return result


def _utc(value: object) -> datetime:
    if type(value) is str:
        try: value = datetime.fromisoformat(value)
        except ValueError: raise ManifestHandoffRegistryUnavailable from None
    if type(value) is not datetime: raise ManifestHandoffRegistryUnavailable
    value = value.replace(tzinfo=value.tzinfo or timezone.utc)
    if value.utcoffset() != timedelta(0): raise ManifestHandoffRegistryUnavailable
    return value


class DatabaseManifestHandoffSupervisorCleanupRevisionMutations:
    """Append source revisions with current persistent source authority."""

    __slots__ = ("_engine", "_clock", "_revision")

    def __init__(self, engine: Engine, *, clock: Callable[[], datetime] | None = None,
                 revision_generator: Callable[[], str] | None = None) -> None:
        if (not isinstance(engine, Engine) or (clock is not None and not callable(clock))
                or (revision_generator is not None and not callable(revision_generator))):
            raise ManifestHandoffRegistryUnavailable
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._revision = revision_generator or (lambda: secrets.token_hex(32))

    def __repr__(self): return "DatabaseManifestHandoffSupervisorCleanupRevisionMutations()"

    def change_control_directory_cleanup_management(self, principal, command):
        if (type(principal) is not SessionPrincipal
                or type(command) is not ChangeManifestHandoffSupervisorControlDirectoryCleanupManagement):
            raise ManifestHandoffRegistryUnavailable
        return self._write_management(principal, command)

    def change_control_directory_cleanup_hold(self, principal, command):
        return self._write_target(_SOURCES["hold"], principal, command)

    def change_control_directory_cleanup_recovery(self, principal, command):
        return self._write_target(_SOURCES["recovery"], principal, command)

    def change_control_directory_cleanup_references(self, principal, command):
        return self._write_target(_SOURCES["reference"], principal, command)

    def _write_management(self, principal, command):
        values = {"change": _encode(command.change_id), "authorizer": _encode(principal.user_id),
            "target": _encode(command.target_user_id), "scope": _encode(command.scope_id),
            "expected": None if command.expected_revision_id is None else _encode(command.expected_revision_id),
            "status": command.status.value}
        def action(connection):
            existing = self._management_retry(connection, values, command)
            if existing is not None: return existing
            authority = self._authority(connection, "management", values["authorizer"], values["scope"])
            if authority is None or not self._active_foundations(connection, values["target"], values["scope"]):
                return None
            latest = self._latest_management(connection, values["target"], values["scope"])
            if not self._expected(latest, values["expected"]):
                return ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict()
            now = _utc(self._clock())
            if latest is not None and now < _utc(latest.resolved_at): raise ManifestHandoffRegistryUnavailable
            if now < authority.created_at: raise ManifestHandoffRegistryUnavailable
            revision = self._new_revision(ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId)
            sequence = 1 if latest is None else latest.sequence_number + 1
            connection.execute(text("INSERT INTO manifest_handoff_supervisor_cleanup_management_revisions"
                " (revision_id,actor_user_id,scope_id,sequence_number,status,resolved_at)"
                " VALUES (:revision,:target,:scope,:sequence,:status,:now)"),
                {**values, "revision": revision, "sequence": sequence, "now": now})
            connection.execute(text("INSERT INTO manifest_handoff_supervisor_cleanup_management_changes"
                " (change_id,revision_id,actor_user_id,scope_id,expected_revision_id)"
                " VALUES (:change,:revision,:target,:scope,:expected)"), {**values, "revision": revision})
            self._insert_authorization(connection, "management", values, authority.revision_id, now)
            fact = ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority(
                ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId(_decode(revision)),
                UserId(_decode(values["target"])), ManifestHandoffRegistryScopeId(_decode(values["scope"])),
                command.status, now)
            return CommittedManifestHandoffSupervisorControlDirectoryCleanupManagementChange(command.change_id, fact)
        return self._access("management", action)

    def _write_target(self, source, principal, command):
        if type(principal) is not SessionPrincipal or type(command) is not source.command_type:
            raise ManifestHandoffRegistryUnavailable
        values = {"change": _encode(command.change_id), "authorizer": _encode(principal.user_id),
            "directory": _encode(command.directory_id),
            "expected": None if command.expected_revision_id is None else _encode(command.expected_revision_id),
            "disposition": command.disposition.value}
        def action(connection):
            existing = self._target_retry(connection, source, values, command)
            if existing is not None: return existing
            retired, scope, terminal_at = self._target(connection, values["directory"])
            values["scope"] = scope
            authority = self._authority(connection, source.kind, values["authorizer"], scope)
            if authority is None: return None
            latest = self._latest_target(connection, source, values["directory"])
            if not self._expected(latest, values["expected"]):
                return ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict()
            now = _utc(self._clock())
            lower = max(retired.retired_at, terminal_at, authority.created_at,
                _utc(latest.decided_at) if latest is not None else retired.retired_at)
            if now < lower: raise ManifestHandoffRegistryUnavailable
            revision = self._new_revision(source.revision_type)
            sequence = 1 if latest is None else latest.sequence_number + 1
            connection.execute(text(f"INSERT INTO {source.revisions}"
                " (revision_id,directory_id,sequence_number,disposition,decided_at)"
                " VALUES (:revision,:directory,:sequence,:disposition,:now)"),
                {**values, "revision": revision, "sequence": sequence, "now": now})
            connection.execute(text(f"INSERT INTO {source.changes}"
                " (change_id,revision_id,directory_id,expected_revision_id)"
                " VALUES (:change,:revision,:directory,:expected)"), {**values, "revision": revision})
            self._insert_authorization(connection, source.kind, values, authority.revision_id, now)
            decision = source.decision_type(source.revision_type(_decode(revision)), retired,
                ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition(values["disposition"]), now)
            return source.result_type(command.change_id, decision)
        return self._access(source.kind, action)

    @dataclass(frozen=True)
    class _Authority:
        revision_id: bytes
        created_at: datetime

    def _authority(self, connection, kind, actor, scope):
        root = f"mh_supervisor_cleanup_{kind}_authority"
        row = self._one(connection, text(f"SELECT current_set.revision_id,sets.created_at"
            f" FROM {root}_current current_set JOIN {root}_sets sets"
            " ON sets.revision_id=current_set.revision_id AND sets.scope_id=current_set.scope_id"
            f" JOIN {root}_members member ON member.revision_id=current_set.revision_id"
            " AND member.scope_id=current_set.scope_id JOIN identity_users users ON users.user_id=member.user_id"
            " JOIN manifest_handoff_registry_scopes scopes ON scopes.scope_id=current_set.scope_id"
            " WHERE current_set.scope_id=:scope AND member.user_id=:actor AND member.status='active'"
            " AND users.status='active' AND scopes.status='active'"), {"scope": scope, "actor": actor}, True)
        return None if row is None else self._Authority(row.revision_id, _utc(row.created_at))

    def _target(self, connection, directory):
        row = self._one(connection, text("SELECT directory.directory_id,directory.handle_id,directory.leaf,"
            " directory.state,directory.reserved_at,directory.activated_at,directory.retired_at,"
            " job.scope_id,transition.kind,transition.observed_at FROM manifest_handoff_supervisor_control_directories directory"
            " JOIN manifest_handoff_supervisor_journal_jobs job ON job.handle_id=directory.handle_id"
            " JOIN manifest_handoff_supervisor_journal_transitions transition ON transition.handle_id=job.handle_id"
            " WHERE directory.directory_id=:directory AND transition.sequence_number=(SELECT max(latest.sequence_number)"
            " FROM manifest_handoff_supervisor_journal_transitions latest WHERE latest.handle_id=job.handle_id)"),
            {"directory": directory}, True)
        if row is None or row.kind != "terminal_observed": raise ManifestHandoffRegistryUnavailable
        retired = DatabaseManifestHandoffSupervisorControlDirectories._lifecycle(row)
        if type(retired) is not RetiredManifestHandoffSupervisorControlDirectory: raise ManifestHandoffRegistryUnavailable
        return retired, row.scope_id, _utc(row.observed_at)

    def _management_retry(self, connection, values, command):
        row = self._one(connection, text("SELECT change.change_id,change.expected_revision_id,change.actor_user_id,"
            " change.scope_id,revision.revision_id,revision.sequence_number,revision.status,revision.resolved_at,"
            " authorization.authorized_by_user_id,authorization.scope_id AS authorized_scope_id"
            " FROM manifest_handoff_supervisor_cleanup_management_changes change"
            " JOIN manifest_handoff_supervisor_cleanup_management_revisions revision ON revision.revision_id=change.revision_id"
            " JOIN mh_supervisor_cleanup_management_change_authorizations authorization ON authorization.change_id=change.change_id"
            " WHERE change.change_id=:change"), values, True)
        if row is None: return None
        if not all((row.actor_user_id == values["target"], row.scope_id == values["scope"],
                row.expected_revision_id == values["expected"], row.status == values["status"],
                row.authorized_by_user_id == values["authorizer"],
                row.authorized_scope_id == values["scope"])):
            return ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict()
        if type(row.sequence_number) is not int or row.sequence_number < 1:
            raise ManifestHandoffRegistryUnavailable
        fact = ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority(
            ManifestHandoffSupervisorControlDirectoryCleanupManagementRevisionId(_decode(row.revision_id)),
            UserId(_decode(row.actor_user_id)), ManifestHandoffRegistryScopeId(_decode(row.scope_id)),
            ManifestHandoffSupervisorControlDirectoryCleanupManagementStatus(row.status), _utc(row.resolved_at))
        return CommittedManifestHandoffSupervisorControlDirectoryCleanupManagementChange(command.change_id, fact)

    def _target_retry(self, connection, source, values, command):
        row = self._one(connection, text(f"SELECT change.expected_revision_id,change.directory_id,revision.revision_id,"
            f" revision.sequence_number,revision.disposition,revision.decided_at,authorization.authorized_by_user_id,"
            " authorization.scope_id AS authorized_scope_id"
            f" FROM {source.changes} change JOIN {source.revisions} revision ON revision.revision_id=change.revision_id"
            f" JOIN {source.authorizations} authorization ON authorization.change_id=change.change_id"
            " WHERE change.change_id=:change"), values, True)
        if row is None: return None
        if not all((row.directory_id == values["directory"], row.expected_revision_id == values["expected"],
                row.disposition == values["disposition"], row.authorized_by_user_id == values["authorizer"])):
            return ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict()
        if type(row.sequence_number) is not int or row.sequence_number < 1:
            raise ManifestHandoffRegistryUnavailable
        retired, scope, _ = self._target(connection, values["directory"])
        if row.authorized_scope_id != scope:
            raise ManifestHandoffRegistryUnavailable
        decision = source.decision_type(source.revision_type(_decode(row.revision_id)), retired,
            ManifestHandoffSupervisorControlDirectoryCleanupClearanceDisposition(row.disposition), _utc(row.decided_at))
        return source.result_type(command.change_id, decision)

    @staticmethod
    def _expected(latest, expected):
        if latest is None: return expected is None
        return latest.revision_id == expected

    def _latest_management(self, connection, target, scope):
        return self._one(connection, text("SELECT revision_id,sequence_number,resolved_at"
            " FROM manifest_handoff_supervisor_cleanup_management_revisions"
            " WHERE actor_user_id=:target AND scope_id=:scope ORDER BY sequence_number DESC LIMIT 1"),
            {"target": target, "scope": scope}, True)

    def _latest_target(self, connection, source, directory):
        return self._one(connection, text(f"SELECT revision_id,sequence_number,decided_at FROM {source.revisions}"
            " WHERE directory_id=:directory ORDER BY sequence_number DESC LIMIT 1"), {"directory": directory}, True)

    @staticmethod
    def _active_foundations(connection, user, scope):
        return connection.execute(text("SELECT 1 FROM identity_users users JOIN manifest_handoff_registry_scopes scopes"
            " ON scopes.scope_id=:scope WHERE users.user_id=:user AND users.status='active' AND scopes.status='active'"),
            {"user": user, "scope": scope}).first() is not None

    @staticmethod
    def _insert_authorization(connection, kind, values, authority_revision, now):
        connection.execute(text(f"INSERT INTO mh_supervisor_cleanup_{kind}_change_authorizations"
            " (change_id,authority_set_revision_id,scope_id,authorized_by_user_id,authorized_at)"
            " VALUES (:change,:authority,:scope,:authorizer,:now)"),
            {**values, "authority": authority_revision, "now": now})

    def _new_revision(self, revision_type):
        try: return _encode(revision_type(self._revision()))
        except (TypeError, ValueError): raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _one(connection, query, values, neutral=False):
        rows = connection.execute(query, values).all()
        if not rows:
            if neutral: return None
            raise ManifestHandoffRegistryUnavailable
        if len(rows) != 1: raise ManifestHandoffRegistryUnavailable
        return rows[0]

    def _access(self, kind, action):
        try:
            with self._engine.begin() as connection:
                if connection.dialect.name == "postgresql":
                    authority = f"mh_supervisor_cleanup_{kind}_authority"
                    revisions = f"manifest_handoff_supervisor_cleanup_{kind}_revisions"
                    changes = f"manifest_handoff_supervisor_cleanup_{kind}_changes"
                    authorizations = f"mh_supervisor_cleanup_{kind}_change_authorizations"
                    connection.execute(text("LOCK TABLE identity_users,manifest_handoff_registry_scopes,"
                        " manifest_handoff_supervisor_control_directories,manifest_handoff_supervisor_journal_jobs,"
                        f" manifest_handoff_supervisor_journal_transitions,{authority}_sets,{authority}_members,"
                        f" {authority}_current,{revisions},{changes},{authorizations} IN SHARE ROW EXCLUSIVE MODE"))
                elif connection.dialect.name != "sqlite": raise ManifestHandoffRegistryUnavailable
                return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None: raise
        except Exception: pass
        raise ManifestHandoffRegistryUnavailable
