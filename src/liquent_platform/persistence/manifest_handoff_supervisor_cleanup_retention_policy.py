"""Persistent bootstrap and current lookups for cleanup retention policy."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import Engine, text

from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention import (
    ManifestHandoffSupervisorCleanupRetentionDataClass,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention_policy import (
    ActiveManifestHandoffSupervisorCleanupRetentionPolicy,
    BootstrapManifestHandoffSupervisorCleanupRetentionPolicy,
    BootstrappedManifestHandoffSupervisorCleanupRetentionPolicy,
    ChangeManifestHandoffSupervisorCleanupRetentionPolicy,
    ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority,
    ChangedManifestHandoffSupervisorCleanupRetentionPolicy,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityMember,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId,
    ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityStatus,
    ManifestHandoffSupervisorCleanupRetentionPolicyConflict,
    ManifestHandoffSupervisorCleanupRetentionPolicyChangeIntent,
    ManifestHandoffSupervisorCleanupRetentionPolicyRevision,
    RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


_CLASS = "supervisor_control_directory"
_POLICIES = "mh_supervisor_cleanup_retention_policy_revisions"
_ACTIVE = "mh_supervisor_cleanup_retention_policy_active"
_SETS = "mh_supervisor_cleanup_retention_policy_authority_sets"
_MEMBERS = "mh_supervisor_cleanup_retention_policy_authority_members"
_CURRENT = "mh_supervisor_cleanup_retention_policy_authority_current"
_BOOTSTRAPS = "mh_supervisor_cleanup_retention_policy_bootstraps"
_CHANGES = "mh_supervisor_cleanup_retention_policy_changes"
_AUTHORITY_CHANGES = "mh_supervisor_cleanup_retention_policy_authority_changes"
_RECOVERIES = "mh_supervisor_cleanup_retention_policy_authority_recoveries"


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


class DatabaseManifestHandoffSupervisorCleanupRetentionPolicy:
    """Atomically bootstrap and freshly resolve the single closed policy."""

    __slots__ = ("_engine", "_clock", "_policy_revision", "_authority_revision")

    def __init__(
        self,
        engine: Engine,
        *,
        clock: Callable[[], datetime],
        policy_revision_generator: Callable[
            [], ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId
        ],
        authority_revision_generator: Callable[
            [], ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId
        ],
    ) -> None:
        if not isinstance(engine, Engine) or not all(
            callable(value)
            for value in (clock, policy_revision_generator, authority_revision_generator)
        ):
            raise ManifestHandoffRegistryUnavailable
        self._engine = engine
        self._clock = clock
        self._policy_revision = policy_revision_generator
        self._authority_revision = authority_revision_generator

    def __repr__(self) -> str:
        return "DatabaseManifestHandoffSupervisorCleanupRetentionPolicy()"

    def resolve_active_cleanup_retention_policy(self):
        def action(connection):
            rows = connection.execute(text(
                f"SELECT policy.revision_id,policy.minimum_retention_seconds,"
                f"policy.created_at,active.activated_at FROM {_ACTIVE} active "
                f"JOIN {_POLICIES} policy ON policy.revision_id=active.revision_id "
                "AND policy.data_class=active.data_class WHERE active.data_class=:class"
            ), {"class": _CLASS}).all()
            if not rows:
                return None
            if len(rows) != 1:
                raise ManifestHandoffRegistryUnavailable
            return self._policy(rows[0])
        return self._access(action, False)

    def permits_cleanup_retention_policy_mutation(self, principal):
        if type(principal) is not SessionPrincipal:
            raise ManifestHandoffRegistryUnavailable
        actor = _encode(principal.user_id)
        def action(connection):
            return self._permits(connection, actor)
        return self._access(action, False)

    def bootstrap_cleanup_retention_policy(self, command):
        if type(command) is not BootstrapManifestHandoffSupervisorCleanupRetentionPolicy:
            raise ManifestHandoffRegistryUnavailable
        values = {
            "id": _encode(command.bootstrap_id),
            "target": _encode(command.target_user_id),
            "class": _CLASS,
            "seconds": int(command.minimum_retention.total_seconds()),
        }
        def action(connection):
            existing = connection.execute(text(
                f"SELECT * FROM {_BOOTSTRAPS} WHERE bootstrap_id=:id"
            ), values).all()
            if existing:
                if len(existing) != 1:
                    raise ManifestHandoffRegistryUnavailable
                row = existing[0]
                if not all((row.target_user_id == values["target"],
                            row.data_class == _CLASS,
                            row.minimum_retention_seconds == values["seconds"])):
                    return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
                return self._load_bootstrap(connection, command, row)
            inventory = connection.execute(text(
                f"SELECT EXISTS (SELECT 1 FROM {_POLICIES}) OR "
                f"EXISTS (SELECT 1 FROM {_SETS}) OR EXISTS (SELECT 1 FROM {_ACTIVE}) OR "
                f"EXISTS (SELECT 1 FROM {_CURRENT}) OR EXISTS (SELECT 1 FROM {_BOOTSTRAPS})"
            )).scalar_one()
            if inventory:
                return None
            active = connection.execute(text(
                "SELECT 1 FROM identity_users WHERE user_id=:target AND status='active'"
            ), values).first()
            if active is None:
                return None
            policy = self._policy_revision()
            authority = self._authority_revision()
            if type(policy) is not ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId:
                raise ManifestHandoffRegistryUnavailable
            if type(authority) is not ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId:
                raise ManifestHandoffRegistryUnavailable
            policy_id, authority_id = _encode(policy), _encode(authority)
            if policy_id == authority_id:
                raise ManifestHandoffRegistryUnavailable
            now = _utc(self._clock())
            connection.execute(text(f"INSERT INTO {_POLICIES} "
                "(revision_id,data_class,minimum_retention_seconds,created_at) "
                "VALUES (:policy,:class,:seconds,:now)"), {**values, "policy": policy_id, "now": now})
            connection.execute(text(f"INSERT INTO {_SETS} "
                "(revision_id,data_class,sequence_number,created_at) "
                "VALUES (:authority,:class,1,:now)"), {**values, "authority": authority_id, "now": now})
            connection.execute(text(f"INSERT INTO {_MEMBERS} "
                "(revision_id,data_class,user_id,status) VALUES (:authority,:class,:target,'active')"),
                {**values, "authority": authority_id})
            connection.execute(text(f"INSERT INTO {_ACTIVE} "
                "(data_class,revision_id,activated_at) VALUES (:class,:policy,:now)"),
                {**values, "policy": policy_id, "now": now})
            connection.execute(text(f"INSERT INTO {_CURRENT} "
                "(data_class,revision_id) VALUES (:class,:authority)"),
                {**values, "authority": authority_id})
            connection.execute(text(f"INSERT INTO {_BOOTSTRAPS} "
                "(bootstrap_id,target_user_id,data_class,policy_revision_id,authority_revision_id,"
                "minimum_retention_seconds,bootstrapped_at) "
                "VALUES (:id,:target,:class,:policy,:authority,:seconds,:now)"),
                {**values, "policy": policy_id, "authority": authority_id, "now": now})
            row = connection.execute(text(f"SELECT * FROM {_BOOTSTRAPS} WHERE bootstrap_id=:id"), values).one()
            return self._load_bootstrap(connection, command, row)
        return self._access(action, True)

    def change_cleanup_retention_policy(self, principal, command):
        if (type(principal) is not SessionPrincipal
                or type(command) is not ChangeManifestHandoffSupervisorCleanupRetentionPolicy):
            raise ManifestHandoffRegistryUnavailable
        values = {
            "id": _encode(command.change_id),
            "actor": _encode(principal.user_id),
            "class": _CLASS,
            "expected": None if command.expected_revision_id is None
            else _encode(command.expected_revision_id),
            "intent": command.intent.value,
            "seconds": None if command.minimum_retention is None
            else int(command.minimum_retention.total_seconds()),
        }
        def action(connection):
            existing = connection.execute(text(
                f"SELECT * FROM {_CHANGES} WHERE change_id=:id"
            ), values).all()
            if existing:
                if len(existing) != 1:
                    raise ManifestHandoffRegistryUnavailable
                row = existing[0]
                if not all((row.actor_user_id == values["actor"],
                            row.data_class == _CLASS,
                            row.expected_revision_id == values["expected"],
                            row.intent == values["intent"],
                            row.minimum_retention_seconds == values["seconds"])):
                    return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
                if row.result_revision_id is None:
                    return ChangedManifestHandoffSupervisorCleanupRetentionPolicy(command, None)
                return ChangedManifestHandoffSupervisorCleanupRetentionPolicy(
                    command, self._load_changed_policy(connection, row)
                )
            if not self._permits(connection, values["actor"]):
                return None
            current = connection.execute(text(
                f"SELECT policy.revision_id,policy.minimum_retention_seconds,"
                f"policy.created_at,active.activated_at FROM {_ACTIVE} active "
                f"JOIN {_POLICIES} policy ON policy.revision_id=active.revision_id "
                "AND policy.data_class=active.data_class WHERE active.data_class=:class"
            ), values).all()
            if len(current) > 1:
                raise ManifestHandoffRegistryUnavailable
            current_id = None if not current else current[0].revision_id
            if current_id != values["expected"]:
                return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
            if values["intent"] == "deactivate":
                if current_id is None or values["seconds"] is not None:
                    return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
                now = _utc(self._clock())
                if now < _utc(current[0].created_at):
                    raise ManifestHandoffRegistryUnavailable
                connection.execute(text(f"DELETE FROM {_ACTIVE} WHERE data_class=:class"), values)
                connection.execute(text(f"INSERT INTO {_CHANGES} "
                    "(change_id,actor_user_id,data_class,expected_revision_id,result_revision_id,"
                    "intent,minimum_retention_seconds,changed_at) "
                    "VALUES (:id,:actor,:class,:expected,NULL,:intent,NULL,:now)"),
                    {**values, "now": now})
                return ChangedManifestHandoffSupervisorCleanupRetentionPolicy(command, None)
            if values["intent"] != "replace" or values["seconds"] is None:
                return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
            maximum = connection.execute(text(f"SELECT MAX(minimum_retention_seconds) "
                f"FROM {_POLICIES} WHERE data_class=:class"), values).scalar_one()
            if type(maximum) is not int or values["seconds"] < maximum:
                return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
            revision = self._policy_revision()
            if type(revision) is not ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId:
                raise ManifestHandoffRegistryUnavailable
            revision_id = _encode(revision)
            if connection.execute(text(f"SELECT 1 FROM {_POLICIES} WHERE revision_id=:revision"),
                                  {"revision": revision_id}).first() is not None:
                return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
            now = _utc(self._clock())
            latest = connection.execute(text(f"SELECT MAX(created_at) FROM {_POLICIES} "
                "WHERE data_class=:class"), values).scalar_one()
            if latest is None or now < _utc(latest):
                raise ManifestHandoffRegistryUnavailable
            connection.execute(text(f"INSERT INTO {_POLICIES} "
                "(revision_id,data_class,minimum_retention_seconds,created_at) "
                "VALUES (:revision,:class,:seconds,:now)"),
                {**values, "revision": revision_id, "now": now})
            updated = connection.execute(text(f"UPDATE {_ACTIVE} SET revision_id=:revision,"
                "activated_at=:now WHERE data_class=:class"),
                {**values, "revision": revision_id, "now": now})
            if updated.rowcount == 0:
                connection.execute(text(f"INSERT INTO {_ACTIVE} "
                    "(data_class,revision_id,activated_at) VALUES (:class,:revision,:now)"),
                    {**values, "revision": revision_id, "now": now})
            connection.execute(text(f"INSERT INTO {_CHANGES} "
                "(change_id,actor_user_id,data_class,expected_revision_id,result_revision_id,"
                "intent,minimum_retention_seconds,changed_at) "
                "VALUES (:id,:actor,:class,:expected,:revision,:intent,:seconds,:now)"),
                {**values, "revision": revision_id, "now": now})
            row = connection.execute(text(f"SELECT * FROM {_CHANGES} WHERE change_id=:id"), values).one()
            return ChangedManifestHandoffSupervisorCleanupRetentionPolicy(
                command, self._load_changed_policy(connection, row)
            )
        return self._access(action, True)

    def change_cleanup_retention_policy_authority(self, principal, command):
        if (type(principal) is not SessionPrincipal
                or type(command)
                is not ChangeManifestHandoffSupervisorCleanupRetentionPolicyAuthority):
            raise ManifestHandoffRegistryUnavailable
        values = {
            "id": _encode(command.change_id),
            "actor": _encode(principal.user_id),
            "target": _encode(command.target_user_id),
            "class": _CLASS,
            "expected": _encode(command.expected_revision_id),
            "intent": command.intent.value,
        }
        def action(connection):
            existing = connection.execute(text(
                f"SELECT * FROM {_AUTHORITY_CHANGES} WHERE change_id=:id"
            ), values).all()
            if existing:
                if len(existing) != 1:
                    raise ManifestHandoffRegistryUnavailable
                row = existing[0]
                if not all((row.actor_user_id == values["actor"],
                            row.target_user_id == values["target"],
                            row.data_class == _CLASS,
                            row.expected_revision_id == values["expected"],
                            row.intent == values["intent"])):
                    return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
                return self._load_authority(connection, row.result_revision_id)
            current = self._current_authority(connection)
            if current is None or current[0] != values["expected"]:
                return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
            revision_id, sequence, created_at, members = current
            if members.get(values["actor"]) != "active":
                return None
            active_users = {row.user_id for row in connection.execute(text(
                "SELECT user_id FROM identity_users WHERE status='active'"
            )).all()}
            if values["actor"] not in active_users or values["target"] not in active_users:
                return None
            previous = members.get(values["target"])
            allowed = ((values["intent"] == "grant" and previous is None)
                       or (values["intent"] == "deactivate" and previous == "active")
                       or (values["intent"] == "reactivate" and previous == "inactive"))
            if not allowed:
                return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
            result_members = dict(members)
            result_members[values["target"]] = (
                "inactive" if values["intent"] == "deactivate" else "active"
            )
            if not any(status == "active" and user in active_users
                       for user, status in result_members.items()):
                return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
            revision = self._authority_revision()
            if type(revision) is not ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId:
                raise ManifestHandoffRegistryUnavailable
            result_id = _encode(revision)
            if result_id == revision_id or connection.execute(text(
                f"SELECT 1 FROM {_SETS} WHERE revision_id=:revision"
            ), {"revision": result_id}).first() is not None:
                return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
            now = _utc(self._clock())
            if now < created_at:
                raise ManifestHandoffRegistryUnavailable
            connection.execute(text(f"INSERT INTO {_SETS} "
                "(revision_id,data_class,sequence_number,created_at) "
                "VALUES (:revision,:class,:sequence,:now)"),
                {**values, "revision": result_id, "sequence": sequence + 1, "now": now})
            for user, status in sorted(result_members.items()):
                connection.execute(text(f"INSERT INTO {_MEMBERS} "
                    "(revision_id,data_class,user_id,status) "
                    "VALUES (:revision,:class,:user,:status)"),
                    {**values, "revision": result_id, "user": user, "status": status})
            updated = connection.execute(text(f"UPDATE {_CURRENT} SET revision_id=:revision "
                "WHERE data_class=:class AND revision_id=:expected"),
                {**values, "revision": result_id})
            if updated.rowcount != 1:
                raise ManifestHandoffRegistryUnavailable
            connection.execute(text(f"INSERT INTO {_AUTHORITY_CHANGES} "
                "(change_id,actor_user_id,target_user_id,data_class,expected_revision_id,"
                "result_revision_id,intent,changed_at) "
                "VALUES (:id,:actor,:target,:class,:expected,:revision,:intent,:now)"),
                {**values, "revision": result_id, "now": now})
            return self._load_authority(connection, result_id)
        return self._access(action, True)

    def recover_cleanup_retention_policy_authority(self, command):
        if type(command) is not RecoverManifestHandoffSupervisorCleanupRetentionPolicyAuthority:
            raise ManifestHandoffRegistryUnavailable
        values = {
            "id": _encode(command.recovery_id),
            "target": _encode(command.target_user_id),
            "class": _CLASS,
            "expected": _encode(command.expected_revision_id),
        }
        def action(connection):
            existing = connection.execute(text(
                f"SELECT * FROM {_RECOVERIES} WHERE recovery_id=:id"
            ), values).all()
            if existing:
                if len(existing) != 1:
                    raise ManifestHandoffRegistryUnavailable
                row = existing[0]
                if not all((row.target_user_id == values["target"],
                            row.data_class == _CLASS,
                            row.expected_revision_id == values["expected"])):
                    return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
                return self._load_authority(connection, row.result_revision_id)
            current = self._current_authority(connection)
            if current is None or current[0] != values["expected"]:
                return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
            revision_id, sequence, created_at, members = current
            if values["target"] not in members:
                return None
            active_users = {row.user_id for row in connection.execute(text(
                "SELECT user_id FROM identity_users WHERE status='active'"
            )).all()}
            if values["target"] not in active_users:
                return None
            if any(status == "active" and user in active_users
                   for user, status in members.items()):
                return None
            result_members = dict(members)
            result_members[values["target"]] = "active"
            revision = self._authority_revision()
            if type(revision) is not ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId:
                raise ManifestHandoffRegistryUnavailable
            result_id = _encode(revision)
            if result_id == revision_id or connection.execute(text(
                f"SELECT 1 FROM {_SETS} WHERE revision_id=:revision"
            ), {"revision": result_id}).first() is not None:
                return ManifestHandoffSupervisorCleanupRetentionPolicyConflict()
            now = _utc(self._clock())
            if now < created_at:
                raise ManifestHandoffRegistryUnavailable
            connection.execute(text(f"INSERT INTO {_SETS} "
                "(revision_id,data_class,sequence_number,created_at) "
                "VALUES (:revision,:class,:sequence,:now)"),
                {**values, "revision": result_id, "sequence": sequence + 1, "now": now})
            for user, status in sorted(result_members.items()):
                connection.execute(text(f"INSERT INTO {_MEMBERS} "
                    "(revision_id,data_class,user_id,status) "
                    "VALUES (:revision,:class,:user,:status)"),
                    {**values, "revision": result_id, "user": user, "status": status})
            updated = connection.execute(text(f"UPDATE {_CURRENT} SET revision_id=:revision "
                "WHERE data_class=:class AND revision_id=:expected"),
                {**values, "revision": result_id})
            if updated.rowcount != 1:
                raise ManifestHandoffRegistryUnavailable
            connection.execute(text(f"INSERT INTO {_RECOVERIES} "
                "(recovery_id,target_user_id,data_class,expected_revision_id,"
                "result_revision_id,recovered_at) "
                "VALUES (:id,:target,:class,:expected,:revision,:now)"),
                {**values, "revision": result_id, "now": now})
            return self._load_authority(connection, result_id)
        return self._access(action, True)

    def _current_authority(self, connection):
        rows = connection.execute(text(f"SELECT sets.revision_id,sets.sequence_number,"
            f"sets.created_at FROM {_CURRENT} current_set JOIN {_SETS} sets "
            "ON sets.revision_id=current_set.revision_id "
            "AND sets.data_class=current_set.data_class WHERE current_set.data_class=:class"),
            {"class": _CLASS}).all()
        if not rows:
            return None
        if len(rows) != 1 or type(rows[0].sequence_number) is not int \
                or rows[0].sequence_number < 1:
            raise ManifestHandoffRegistryUnavailable
        members = self._member_rows(connection, rows[0].revision_id)
        return (rows[0].revision_id, rows[0].sequence_number,
                _utc(rows[0].created_at), members)

    def _member_rows(self, connection, revision):
        rows = connection.execute(text(f"SELECT user_id,status FROM {_MEMBERS} "
            "WHERE revision_id=:revision AND data_class=:class ORDER BY user_id"),
            {"revision": revision, "class": _CLASS}).all()
        if not rows:
            raise ManifestHandoffRegistryUnavailable
        members = {row.user_id: row.status for row in rows}
        if len(members) != len(rows) or any(status not in ("active", "inactive")
                                           for status in members.values()):
            raise ManifestHandoffRegistryUnavailable
        return members

    def _permits(self, connection, actor):
        rows = connection.execute(text(
            f"SELECT 1 FROM {_CURRENT} current_set JOIN {_MEMBERS} member "
            "ON member.revision_id=current_set.revision_id "
            "AND member.data_class=current_set.data_class JOIN identity_users users "
            "ON users.user_id=member.user_id WHERE current_set.data_class=:class "
            "AND member.user_id=:actor AND member.status='active' AND users.status='active'"
        ), {"class": _CLASS, "actor": actor}).all()
        if len(rows) > 1:
            raise ManifestHandoffRegistryUnavailable
        return bool(rows)

    def _load_changed_policy(self, connection, change):
        rows = connection.execute(text(f"SELECT revision_id,minimum_retention_seconds,created_at,"
            f":activated AS activated_at FROM {_POLICIES} WHERE revision_id=:revision "
            "AND data_class=:class"), {"revision": change.result_revision_id,
            "class": _CLASS, "activated": change.changed_at}).all()
        if len(rows) != 1:
            raise ManifestHandoffRegistryUnavailable
        return self._policy(rows[0])

    def _load_bootstrap(self, connection, command, bootstrap):
        policy_rows = connection.execute(text(f"SELECT revision_id,minimum_retention_seconds,"
            f"created_at,:activated AS activated_at FROM {_POLICIES} "
            "WHERE revision_id=:revision AND data_class=:class"),
            {"revision": bootstrap.policy_revision_id, "class": _CLASS,
             "activated": bootstrap.bootstrapped_at}).all()
        if len(policy_rows) != 1:
            raise ManifestHandoffRegistryUnavailable
        authority = self._load_authority(connection, bootstrap.authority_revision_id)
        return BootstrappedManifestHandoffSupervisorCleanupRetentionPolicy(
            command, self._policy(policy_rows[0]), authority
        )

    def _load_authority(self, connection, revision):
        sets = connection.execute(text(f"SELECT sequence_number FROM {_SETS} "
            "WHERE revision_id=:revision AND data_class=:class"),
            {"revision": revision, "class": _CLASS}).all()
        members = self._member_rows(connection, revision)
        if len(sets) != 1 or type(sets[0].sequence_number) is not int or sets[0].sequence_number < 1:
            raise ManifestHandoffRegistryUnavailable
        try:
            members = frozenset(ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityMember(
                _decode(user),
                ManifestHandoffSupervisorCleanupRetentionPolicyAuthorityStatus(status),
            ) for user, status in members.items())
            return ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySet(
                ManifestHandoffSupervisorCleanupRetentionPolicyAuthoritySetRevisionId(_decode(revision)), members
            )
        except (TypeError, ValueError):
            raise ManifestHandoffRegistryUnavailable from None

    @staticmethod
    def _policy(row):
        try:
            seconds = row.minimum_retention_seconds
            if type(seconds) is not int or seconds <= 0:
                raise ManifestHandoffRegistryUnavailable
            policy = ManifestHandoffSupervisorCleanupRetentionPolicyRevision(
                ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId(_decode(row.revision_id)),
                ManifestHandoffSupervisorCleanupRetentionDataClass.SUPERVISOR_CONTROL_DIRECTORY,
                timedelta(seconds=seconds), _utc(row.created_at),
            )
            return ActiveManifestHandoffSupervisorCleanupRetentionPolicy(policy, _utc(row.activated_at))
        except (TypeError, ValueError, OverflowError):
            raise ManifestHandoffRegistryUnavailable from None

    def _access(self, action, write):
        try:
            context = self._engine.begin() if write else self._engine.connect()
            with context as connection:
                if connection.dialect.name == "postgresql" and write:
                    connection.execute(text("LOCK TABLE identity_users,"
                        f"{_POLICIES},{_ACTIVE},{_SETS},{_MEMBERS},{_CURRENT},{_BOOTSTRAPS},"
                        f"{_CHANGES},{_AUTHORITY_CHANGES},{_RECOVERIES} "
                        "IN SHARE ROW EXCLUSIVE MODE"))
                elif connection.dialect.name not in ("postgresql", "sqlite"):
                    raise ManifestHandoffRegistryUnavailable
                return action(connection)
        except ManifestHandoffRegistryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise ManifestHandoffRegistryUnavailable
