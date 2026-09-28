"""Persistent authority sets for supervisor cleanup revision mutation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets

from sqlalchemy import Engine, text

from liquent_platform.identity.manifest_handoff import ManifestHandoffRegistryScopeId
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_mutation_authority import (
    BootstrapCleanupHoldMutationAuthority,
    BootstrapCleanupManagementMutationAuthority,
    BootstrapCleanupRecoveryMutationAuthority,
    BootstrapCleanupReferenceMutationAuthority,
    ChangeCleanupHoldMutationAuthority,
    ChangeCleanupManagementMutationAuthority,
    ChangeCleanupRecoveryMutationAuthority,
    ChangeCleanupReferenceMutationAuthority,
    CleanupHoldMutationAuthorityBootstrapId,
    CleanupHoldMutationAuthorityLifecycleChangeId,
    CleanupHoldMutationAuthorityRecoveryId,
    CleanupHoldMutationAuthoritySet,
    CleanupHoldMutationAuthoritySetRevisionId,
    CleanupManagementMutationAuthorityBootstrapId,
    CleanupManagementMutationAuthorityLifecycleChangeId,
    CleanupManagementMutationAuthorityRecoveryId,
    CleanupManagementMutationAuthoritySet,
    CleanupManagementMutationAuthoritySetRevisionId,
    CleanupRecoveryMutationAuthorityBootstrapId,
    CleanupRecoveryMutationAuthorityLifecycleChangeId,
    CleanupRecoveryMutationAuthorityRecoveryId,
    CleanupRecoveryMutationAuthoritySet,
    CleanupRecoveryMutationAuthoritySetRevisionId,
    CleanupReferenceMutationAuthorityBootstrapId,
    CleanupReferenceMutationAuthorityLifecycleChangeId,
    CleanupReferenceMutationAuthorityRecoveryId,
    CleanupReferenceMutationAuthoritySet,
    CleanupReferenceMutationAuthoritySetRevisionId,
    ManifestHandoffSupervisorCleanupMutationAuthorityConflict,
    ManifestHandoffSupervisorCleanupMutationAuthorityLifecycleIntent,
    ManifestHandoffSupervisorCleanupMutationAuthorityMember,
    ManifestHandoffSupervisorCleanupMutationAuthorityStatus,
    RecoverCleanupHoldMutationAuthority,
    RecoverCleanupManagementMutationAuthority,
    RecoverCleanupRecoveryMutationAuthority,
    RecoverCleanupReferenceMutationAuthority,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


@dataclass(frozen=True)
class _Source:
    kind: str
    revision_type: type
    set_type: type
    bootstrap_type: type
    bootstrap_id_type: type
    change_type: type
    change_id_type: type
    recovery_type: type
    recovery_id_type: type

    @property
    def root(self):
        return f"mh_supervisor_cleanup_{self.kind}_authority"


_SOURCES = {
    "management": _Source("management", CleanupManagementMutationAuthoritySetRevisionId,
        CleanupManagementMutationAuthoritySet, BootstrapCleanupManagementMutationAuthority,
        CleanupManagementMutationAuthorityBootstrapId, ChangeCleanupManagementMutationAuthority,
        CleanupManagementMutationAuthorityLifecycleChangeId, RecoverCleanupManagementMutationAuthority,
        CleanupManagementMutationAuthorityRecoveryId),
    "hold": _Source("hold", CleanupHoldMutationAuthoritySetRevisionId,
        CleanupHoldMutationAuthoritySet, BootstrapCleanupHoldMutationAuthority,
        CleanupHoldMutationAuthorityBootstrapId, ChangeCleanupHoldMutationAuthority,
        CleanupHoldMutationAuthorityLifecycleChangeId, RecoverCleanupHoldMutationAuthority,
        CleanupHoldMutationAuthorityRecoveryId),
    "recovery": _Source("recovery", CleanupRecoveryMutationAuthoritySetRevisionId,
        CleanupRecoveryMutationAuthoritySet, BootstrapCleanupRecoveryMutationAuthority,
        CleanupRecoveryMutationAuthorityBootstrapId, ChangeCleanupRecoveryMutationAuthority,
        CleanupRecoveryMutationAuthorityLifecycleChangeId, RecoverCleanupRecoveryMutationAuthority,
        CleanupRecoveryMutationAuthorityRecoveryId),
    "reference": _Source("reference", CleanupReferenceMutationAuthoritySetRevisionId,
        CleanupReferenceMutationAuthoritySet, BootstrapCleanupReferenceMutationAuthority,
        CleanupReferenceMutationAuthorityBootstrapId, ChangeCleanupReferenceMutationAuthority,
        CleanupReferenceMutationAuthorityLifecycleChangeId, RecoverCleanupReferenceMutationAuthority,
        CleanupReferenceMutationAuthorityRecoveryId),
}


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


class DatabaseManifestHandoffSupervisorCleanupMutationAuthorities:
    """Persist four source-specific complete authority-set histories."""

    __slots__ = ("_engine", "_clock", "_revision")

    def __init__(self, engine: Engine, *, clock: Callable[[], datetime] | None = None,
                 revision_generator: Callable[[], str] | None = None) -> None:
        if (not isinstance(engine, Engine) or (clock is not None and not callable(clock))
                or (revision_generator is not None and not callable(revision_generator))):
            raise ManifestHandoffRegistryUnavailable
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._revision = revision_generator or (lambda: secrets.token_hex(32))

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffSupervisorCleanupMutationAuthorities()"

    def permits_cleanup_management_mutation(self, principal, scope_id):
        return self._permits(_SOURCES["management"], principal, scope_id)

    def permits_cleanup_hold_mutation(self, principal, scope_id):
        return self._permits(_SOURCES["hold"], principal, scope_id)

    def permits_cleanup_recovery_mutation(self, principal, scope_id):
        return self._permits(_SOURCES["recovery"], principal, scope_id)

    def permits_cleanup_reference_mutation(self, principal, scope_id):
        return self._permits(_SOURCES["reference"], principal, scope_id)

    def bootstrap_cleanup_management_mutation_authority(self, command):
        return self._bootstrap(_SOURCES["management"], command)

    def bootstrap_cleanup_hold_mutation_authority(self, command):
        return self._bootstrap(_SOURCES["hold"], command)

    def bootstrap_cleanup_recovery_mutation_authority(self, command):
        return self._bootstrap(_SOURCES["recovery"], command)

    def bootstrap_cleanup_reference_mutation_authority(self, command):
        return self._bootstrap(_SOURCES["reference"], command)

    def change_cleanup_management_mutation_authority(self, principal, command):
        return self._change(_SOURCES["management"], principal, command)

    def change_cleanup_hold_mutation_authority(self, principal, command):
        return self._change(_SOURCES["hold"], principal, command)

    def change_cleanup_recovery_mutation_authority(self, principal, command):
        return self._change(_SOURCES["recovery"], principal, command)

    def change_cleanup_reference_mutation_authority(self, principal, command):
        return self._change(_SOURCES["reference"], principal, command)

    def recover_cleanup_management_mutation_authority(self, command):
        return self._recover(_SOURCES["management"], command)

    def recover_cleanup_hold_mutation_authority(self, command):
        return self._recover(_SOURCES["hold"], command)

    def recover_cleanup_recovery_mutation_authority(self, command):
        return self._recover(_SOURCES["recovery"], command)

    def recover_cleanup_reference_mutation_authority(self, command):
        return self._recover(_SOURCES["reference"], command)

    def _permits(self, source, principal, scope_id):
        if type(principal) is not SessionPrincipal or type(scope_id) is not ManifestHandoffRegistryScopeId:
            raise ManifestHandoffRegistryUnavailable
        root = source.root
        query = text(
            f"SELECT 1 FROM {root}_current current_set"
            f" JOIN {root}_members member ON member.revision_id=current_set.revision_id"
            " AND member.scope_id=current_set.scope_id"
            " JOIN identity_users users ON users.user_id=member.user_id"
            " JOIN manifest_handoff_registry_scopes scopes ON scopes.scope_id=current_set.scope_id"
            " WHERE current_set.scope_id=:scope AND member.user_id=:actor"
            " AND member.status='active' AND users.status='active' AND scopes.status='active'"
        )
        return self._read(lambda connection: connection.execute(query, {
            "scope": _encode(scope_id), "actor": _encode(principal.user_id)}).first() is not None)

    def _bootstrap(self, source, command):
        if type(command) is not source.bootstrap_type:
            raise ManifestHandoffRegistryUnavailable
        root = source.root
        values = {"id": _encode(command.bootstrap_id), "target": _encode(command.target_user_id),
            "scope": _encode(command.scope_id)}
        def action(connection):
            existing = self._one(connection, text(
                f"SELECT * FROM {root}_bootstraps WHERE bootstrap_id=:id"), values, True)
            if existing is not None:
                if existing.target_user_id != values["target"] or existing.scope_id != values["scope"]:
                    return ManifestHandoffSupervisorCleanupMutationAuthorityConflict()
                return self._load_set(connection, source, existing.result_revision_id, values["scope"])
            if connection.execute(text(f"SELECT 1 FROM {root}_sets WHERE scope_id=:scope"), values).first():
                return None
            if not self._active_foundations(connection, values["target"], values["scope"]):
                return None
            revision = self._new_revision(source)
            now = _utc(self._clock())
            self._insert_set(connection, source, revision, values["scope"], 1,
                {values["target"]: "active"}, now)
            connection.execute(text(
                f"INSERT INTO {root}_bootstraps"
                " (bootstrap_id,target_user_id,scope_id,result_revision_id,bootstrapped_at)"
                " VALUES (:id,:target,:scope,:result,:now)"),
                {**values, "result": revision, "now": now})
            return self._load_set(connection, source, revision, values["scope"])
        return self._write(source, action)

    def _change(self, source, principal, command):
        if type(principal) is not SessionPrincipal or type(command) is not source.change_type:
            raise ManifestHandoffRegistryUnavailable
        root = source.root
        values = {"id": _encode(command.change_id), "actor": _encode(principal.user_id),
            "target": _encode(command.target_user_id), "scope": _encode(command.scope_id),
            "expected": _encode(command.expected_revision_id), "intent": command.intent.value}
        def action(connection):
            existing = self._one(connection, text(
                f"SELECT * FROM {root}_changes WHERE change_id=:id"), values, True)
            if existing is not None:
                if not all((existing.actor_user_id == values["actor"],
                        existing.target_user_id == values["target"], existing.scope_id == values["scope"],
                        existing.expected_revision_id == values["expected"], existing.intent == values["intent"])):
                    return ManifestHandoffSupervisorCleanupMutationAuthorityConflict()
                return self._load_set(connection, source, existing.result_revision_id, values["scope"])
            current = self._current(connection, source, values["scope"])
            if current is None or current.revision_id != values["expected"]:
                return ManifestHandoffSupervisorCleanupMutationAuthorityConflict()
            if not all((self._active_foundations(connection, values["actor"], values["scope"]),
                    self._active_foundations(connection, values["target"], values["scope"]),
                    current.members.get(values["actor"]) == "active")):
                return None
            members = dict(current.members)
            previous = members.get(values["target"])
            allowed = ((values["intent"] == "grant" and previous is None)
                or (values["intent"] == "deactivate" and previous == "active")
                or (values["intent"] == "reactivate" and previous == "inactive"))
            if not allowed:
                return ManifestHandoffSupervisorCleanupMutationAuthorityConflict()
            members[values["target"]] = "inactive" if values["intent"] == "deactivate" else "active"
            if not self._has_effective_member(connection, members, values["scope"]):
                return ManifestHandoffSupervisorCleanupMutationAuthorityConflict()
            revision = self._new_revision(source); now = _utc(self._clock())
            if now < current.created_at:
                raise ManifestHandoffRegistryUnavailable
            self._insert_set(connection, source, revision, values["scope"], current.sequence + 1, members, now)
            connection.execute(text(
                f"INSERT INTO {root}_changes"
                " (change_id,actor_user_id,target_user_id,scope_id,expected_revision_id,"
                " result_revision_id,intent,changed_at)"
                " VALUES (:id,:actor,:target,:scope,:expected,:result,:intent,:now)"),
                {**values, "result": revision, "now": now})
            return self._load_set(connection, source, revision, values["scope"])
        return self._write(source, action)

    def _recover(self, source, command):
        if type(command) is not source.recovery_type:
            raise ManifestHandoffRegistryUnavailable
        root = source.root
        values = {"id": _encode(command.recovery_id), "target": _encode(command.target_user_id),
            "scope": _encode(command.scope_id), "expected": _encode(command.expected_revision_id)}
        def action(connection):
            existing = self._one(connection, text(
                f"SELECT * FROM {root}_recoveries WHERE recovery_id=:id"), values, True)
            if existing is not None:
                if not all((existing.target_user_id == values["target"], existing.scope_id == values["scope"],
                        existing.expected_revision_id == values["expected"])):
                    return ManifestHandoffSupervisorCleanupMutationAuthorityConflict()
                return self._load_set(connection, source, existing.result_revision_id, values["scope"])
            current = self._current(connection, source, values["scope"])
            if current is None or current.revision_id != values["expected"]:
                return ManifestHandoffSupervisorCleanupMutationAuthorityConflict()
            if (values["target"] not in current.members
                    or not self._active_foundations(connection, values["target"], values["scope"])
                    or self._effective_count(connection, source, values["scope"]) != 0):
                return None
            members = dict(current.members); members[values["target"]] = "active"
            revision = self._new_revision(source); now = _utc(self._clock())
            if now < current.created_at:
                raise ManifestHandoffRegistryUnavailable
            self._insert_set(connection, source, revision, values["scope"], current.sequence + 1, members, now)
            connection.execute(text(
                f"INSERT INTO {root}_recoveries"
                " (recovery_id,target_user_id,scope_id,expected_revision_id,result_revision_id,recovered_at)"
                " VALUES (:id,:target,:scope,:expected,:result,:now)"),
                {**values, "result": revision, "now": now})
            return self._load_set(connection, source, revision, values["scope"])
        return self._write(source, action)

    @dataclass(frozen=True)
    class _Current:
        revision_id: bytes
        sequence: int
        created_at: datetime
        members: dict

    def _current(self, connection, source, scope):
        root = source.root
        row = self._one(connection, text(
            f"SELECT sets.revision_id,sets.sequence_number,sets.created_at FROM {root}_current current_set"
            f" JOIN {root}_sets sets ON sets.revision_id=current_set.revision_id"
            " AND sets.scope_id=current_set.scope_id WHERE current_set.scope_id=:scope"),
            {"scope": scope}, True)
        if row is None:
            return None
        if type(row.sequence_number) is not int or row.sequence_number < 1:
            raise ManifestHandoffRegistryUnavailable
        members = self._member_rows(connection, source, row.revision_id, scope)
        return self._Current(row.revision_id, row.sequence_number, _utc(row.created_at), members)

    def _insert_set(self, connection, source, revision, scope, sequence, members, now):
        root = source.root
        connection.execute(text(f"INSERT INTO {root}_sets"
            " (revision_id,scope_id,sequence_number,created_at) VALUES (:revision,:scope,:sequence,:now)"),
            {"revision": revision, "scope": scope, "sequence": sequence, "now": now})
        for user, status in members.items():
            connection.execute(text(f"INSERT INTO {root}_members"
                " (revision_id,scope_id,user_id,status) VALUES (:revision,:scope,:user,:status)"),
                {"revision": revision, "scope": scope, "user": user, "status": status})
        updated = connection.execute(text(f"UPDATE {root}_current SET revision_id=:revision"
            " WHERE scope_id=:scope"), {"revision": revision, "scope": scope})
        if updated.rowcount == 0:
            connection.execute(text(f"INSERT INTO {root}_current (scope_id,revision_id)"
                " VALUES (:scope,:revision)"), {"scope": scope, "revision": revision})

    def _load_set(self, connection, source, revision, scope):
        row = self._one(connection, text(f"SELECT sequence_number FROM {source.root}_sets"
            " WHERE revision_id=:revision AND scope_id=:scope"),
            {"revision": revision, "scope": scope})
        if type(row.sequence_number) is not int or row.sequence_number < 1:
            raise ManifestHandoffRegistryUnavailable
        members = self._member_rows(connection, source, revision, scope)
        domain_members = frozenset(ManifestHandoffSupervisorCleanupMutationAuthorityMember(
            _decode(user), ManifestHandoffSupervisorCleanupMutationAuthorityStatus(status))
            for user, status in members.items())
        return source.set_type(source.revision_type(_decode(revision)),
            ManifestHandoffRegistryScopeId(_decode(scope)), domain_members)

    def _member_rows(self, connection, source, revision, scope):
        rows = connection.execute(text(f"SELECT user_id,status FROM {source.root}_members"
            " WHERE revision_id=:revision AND scope_id=:scope ORDER BY user_id"),
            {"revision": revision, "scope": scope}).all()
        if not rows:
            raise ManifestHandoffRegistryUnavailable
        members = {row.user_id: row.status for row in rows}
        if len(members) != len(rows):
            raise ManifestHandoffRegistryUnavailable
        return members

    @staticmethod
    def _active_foundations(connection, user, scope):
        return connection.execute(text("SELECT 1 FROM identity_users users"
            " JOIN manifest_handoff_registry_scopes scopes ON scopes.scope_id=:scope"
            " WHERE users.user_id=:user AND users.status='active' AND scopes.status='active'"),
            {"user": user, "scope": scope}).first() is not None

    def _effective_count(self, connection, source, scope):
        return connection.execute(text(f"SELECT count(*) FROM {source.root}_current current_set"
            f" JOIN {source.root}_members member ON member.revision_id=current_set.revision_id"
            " AND member.scope_id=current_set.scope_id JOIN identity_users users"
            " ON users.user_id=member.user_id WHERE current_set.scope_id=:scope"
            " AND member.status='active' AND users.status='active'"), {"scope": scope}).scalar_one()

    @staticmethod
    def _has_effective_member(connection, members, scope):
        active = [user for user, status in members.items() if status == "active"]
        if not active:
            return False
        rows = connection.execute(text("SELECT user_id FROM identity_users"
            " WHERE status='active'"), {}).all()
        active_users = {row.user_id for row in rows}
        scope_active = connection.execute(text("SELECT 1 FROM manifest_handoff_registry_scopes"
            " WHERE scope_id=:scope AND status='active'"), {"scope": scope}).first()
        return scope_active is not None and any(user in active_users for user in active)

    def _new_revision(self, source):
        value = self._revision()
        try:
            return _encode(source.revision_type(value))
        except (TypeError, ValueError):
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _one(connection, query, values, neutral=False):
        rows = connection.execute(query, values).all()
        if not rows:
            if neutral: return None
            raise ManifestHandoffRegistryUnavailable
        if len(rows) != 1: raise ManifestHandoffRegistryUnavailable
        return rows[0]

    def _write(self, source, action):
        return self._access(source, action, True)

    def _read(self, action):
        return self._access(None, action, False)

    def _access(self, source, action, write):
        try:
            context = self._engine.begin() if write else self._engine.connect()
            with context as connection:
                if connection.dialect.name == "postgresql":
                    if write:
                        root = source.root
                        connection.execute(text("LOCK TABLE identity_users,manifest_handoff_registry_scopes,"
                            f" {root}_sets,{root}_members,{root}_current,{root}_bootstraps,"
                            f" {root}_changes,{root}_recoveries IN SHARE ROW EXCLUSIVE MODE"))
                elif connection.dialect.name != "sqlite":
                    raise ManifestHandoffRegistryUnavailable
                return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None: raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable
