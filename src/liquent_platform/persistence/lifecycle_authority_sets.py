"""Anchoring and regular mutation of separate lifecycle authority sets."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, Engine, Row, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.lifecycle import (
    AnchoredUserLifecycleAuthoritySet,
    AnchoredWorkspaceLifecycleAuthoritySet,
    AuthorizedUserLifecycleAuthorityChange,
    AuthorizedWorkspaceLifecycleAuthorityChange,
    LifecycleAuthorityIntent,
    UserLifecycleAuthorityChangeId,
    UserLifecycleAuthoritySetRevisionId,
    WorkspaceLifecycleAuthorityChangeId,
    WorkspaceLifecycleAuthoritySetRevisionId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    LifecycleAuthoritySetConflict,
    LifecycleAuthoritySetUnavailable,
)


@dataclass(frozen=True)
class _Domain:
    prefix: str
    authorities: str
    change_type: type
    revision_type: type
    anchored_type: type
    result_type: type


_USER = _Domain(
    "user_lifecycle", "user_lifecycle_management_authorities",
    UserLifecycleAuthorityChangeId, UserLifecycleAuthoritySetRevisionId,
    AnchoredUserLifecycleAuthoritySet, AuthorizedUserLifecycleAuthorityChange,
)
_WORKSPACE = _Domain(
    "workspace_lifecycle", "workspace_lifecycle_management_authorities",
    WorkspaceLifecycleAuthorityChangeId, WorkspaceLifecycleAuthoritySetRevisionId,
    AnchoredWorkspaceLifecycleAuthoritySet,
    AuthorizedWorkspaceLifecycleAuthorityChange,
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise LifecycleAuthoritySetUnavailable
    return value.encode("utf-8")


def _stored(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
        raise LifecycleAuthoritySetUnavailable
    return bytes(value)


def _decode(value: object) -> str:
    try:
        result = _stored(value).decode("utf-8")
    except UnicodeDecodeError:
        raise LifecycleAuthoritySetUnavailable from None
    if not result:
        raise LifecycleAuthoritySetUnavailable
    return result


class _LifecycleAuthoritySets:
    __slots__ = ("_engine", "_generate_revision_id", "_domain")

    def __init__(
        self,
        engine: Engine,
        domain: _Domain,
        *,
        generate_revision_id: Callable[[], Any],
    ) -> None:
        self._engine = engine
        self._domain = domain
        self._generate_revision_id = generate_revision_id

    def _names(self) -> tuple[str, str, str, str]:
        prefix = self._domain.prefix
        return (
            f"{prefix}_authority_set_revisions",
            f"{prefix}_authority_set_members",
            f"{prefix}_authority_current_set",
            f"{prefix}_authority_changes",
        )

    def _run(self, operation: Callable[[], Any]) -> Any:
        try:
            return operation()
        except LifecycleAuthoritySetConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = LifecycleAuthoritySetConflict
        except LifecycleAuthoritySetUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = LifecycleAuthoritySetUnavailable
        except Exception:
            failure = LifecycleAuthoritySetUnavailable
        raise failure()

    def anchor(self, change_id: Any, principal: SessionPrincipal) -> Any | None:
        return self._run(lambda: self._anchor(change_id, principal))

    def _anchor(self, change_id: Any, principal: SessionPrincipal) -> Any | None:
        if type(change_id) is not self._domain.change_type:
            raise LifecycleAuthoritySetUnavailable
        if type(principal) is not SessionPrincipal:
            raise LifecycleAuthoritySetUnavailable
        revisions, members, current, changes = self._names()
        change = _encode(change_id.value)
        actor = _encode(principal.user_id)
        with self._engine.begin() as transaction:
            self._dialect_and_lock(
                transaction, revisions, members, current, changes
            )
            existing = transaction.execute(text(
                f"SELECT * FROM {changes} WHERE change_id=:change"
            ), {"change": change}).first()
            if existing is not None:
                return self._resolve_anchor(
                    transaction, existing, change_id, actor, revisions
                )
            empty = transaction.scalar(text(
                f"SELECT NOT EXISTS (SELECT 1 FROM {revisions}) AND "
                f"NOT EXISTS (SELECT 1 FROM {current}) AND "
                f"NOT EXISTS (SELECT 1 FROM {changes})"
            ))
            if not empty or transaction.execute(text(
                "SELECT 1 FROM identity_users AS users JOIN "
                f"{self._domain.authorities} AS authority "
                "ON authority.user_id=users.user_id "
                "WHERE users.user_id=:actor AND users.status='active' "
                "AND authority.status='active'"
            ), {"actor": actor}).first() is None:
                return None
            inventory = transaction.execute(text(
                f"SELECT user_id,status FROM {self._domain.authorities} "
                "ORDER BY user_id"
            )).all()
            if not inventory:
                return None
            revision_id = self._new_revision()
            revision = _encode(revision_id.value)
            transaction.execute(text(
                f"INSERT INTO {revisions} VALUES (:revision)"
            ), {"revision": revision})
            for row in inventory:
                transaction.execute(text(
                    f"INSERT INTO {members} VALUES (:revision,:user,:status)"
                ), {"revision": revision, "user": _stored(row.user_id),
                    "status": row.status})
            transaction.execute(text(
                f"INSERT INTO {current} VALUES (1,:revision)"
            ), {"revision": revision})
            transaction.execute(text(
                f"INSERT INTO {changes} VALUES "
                "(:change,:actor,:actor,'anchor',NULL,:revision)"
            ), {"change": change, "actor": actor, "revision": revision})
            return self._domain.anchored_type(change_id, revision_id)

    def change_authority(
        self, change_id: Any, principal: SessionPrincipal, target_user_id: UserId,
        intent: LifecycleAuthorityIntent, expected_revision: Any,
    ) -> Any | None:
        return self._run(lambda: self._change(
            change_id, principal, target_user_id, intent, expected_revision
        ))

    def _change(
        self, change_id: Any, principal: SessionPrincipal, target_user_id: UserId,
        intent: LifecycleAuthorityIntent, expected_revision: Any,
    ) -> Any | None:
        if (
            type(change_id) is not self._domain.change_type
            or type(principal) is not SessionPrincipal
            or type(intent) is not LifecycleAuthorityIntent
            or type(expected_revision) is not self._domain.revision_type
        ):
            raise LifecycleAuthoritySetUnavailable
        revisions, members, current, changes = self._names()
        parameters = {
            "change": _encode(change_id.value), "actor": _encode(principal.user_id),
            "target": _encode(target_user_id),
            "expected": _encode(expected_revision.value), "intent": intent.value,
        }
        with self._engine.begin() as transaction:
            self._dialect_and_lock(transaction, revisions, members, current, changes)
            existing = transaction.execute(text(
                f"SELECT * FROM {changes} WHERE change_id=:change"
            ), parameters).first()
            if existing is not None:
                return self._resolve_change(
                    transaction, existing, change_id, intent, parameters, revisions
                )
            permitted = transaction.execute(text(
                "SELECT 1 FROM identity_users AS actor JOIN "
                f"{self._domain.authorities} AS authority "
                "ON authority.user_id=actor.user_id JOIN identity_users AS target "
                "ON target.user_id=:target WHERE actor.user_id=:actor "
                "AND actor.status='active' AND target.status='active' "
                "AND authority.status='active'"
            ), parameters).first()
            current_revision = transaction.scalar(text(
                f"SELECT revision_id FROM {current} WHERE singleton_key=1"
            ))
            if permitted is None or current_revision is None:
                return None
            if _stored(current_revision) != parameters["expected"]:
                return None
            inventory = transaction.execute(text(
                "SELECT authority.user_id,authority.status,"
                "users.status AS user_status "
                f"FROM {self._domain.authorities} AS authority "
                "JOIN identity_users AS users "
                "ON users.user_id=authority.user_id ORDER BY authority.user_id"
            )).all()
            next_set = self._transition(inventory, parameters["target"], intent)
            if next_set is None:
                return None
            revision_id = self._new_revision()
            revision = _encode(revision_id.value)
            transaction.execute(text(f"INSERT INTO {revisions} VALUES (:revision)"),
                                {"revision": revision})
            for user, status in next_set:
                transaction.execute(text(
                    f"INSERT INTO {members} VALUES (:revision,:user,:status)"
                ), {"revision": revision, "user": user, "status": status})
            if intent is LifecycleAuthorityIntent.GRANT:
                transaction.execute(
                    text(
                        f"INSERT INTO {self._domain.authorities}"
                        " VALUES (:target,'active')"
                    ),
                    parameters,
                )
            else:
                target_status = next(
                    status
                    for user, status in next_set
                    if user == parameters["target"]
                )
                transaction.execute(
                    text(
                        f"UPDATE {self._domain.authorities} SET status=:status "
                        "WHERE user_id=:target"
                    ),
                    {"target": parameters["target"], "status": target_status},
                )
            transaction.execute(text(
                f"UPDATE {current} SET revision_id=:revision WHERE singleton_key=1"
            ), {"revision": revision})
            transaction.execute(text(
                f"INSERT INTO {changes} VALUES "
                "(:change,:actor,:target,:intent,:expected,:revision)"
            ), dict(parameters, revision=revision))
            return self._domain.result_type(
                change_id, revision_id, UserId(str(target_user_id)), intent
            )

    def _new_revision(self) -> Any:
        revision = self._generate_revision_id()
        if type(revision) is not self._domain.revision_type:
            raise LifecycleAuthoritySetUnavailable
        return revision

    def _dialect_and_lock(
        self, transaction: Connection, revisions: str, members: str,
        current: str, changes: str,
    ) -> None:
        if transaction.dialect.name == "postgresql":
            transaction.execute(text(
                "LOCK TABLE identity_users, "
                f"{self._domain.authorities}, {revisions}, {members}, {current}, "
                f"{changes} IN SHARE ROW EXCLUSIVE MODE"
            ))
        elif transaction.dialect.name != "sqlite":
            raise LifecycleAuthoritySetUnavailable

    @staticmethod
    def _transition(rows: list[Any], target: bytes, intent: LifecycleAuthorityIntent):
        states = {_stored(row.user_id): (row.status, row.user_status) for row in rows}
        current = states.get(target)
        if intent is LifecycleAuthorityIntent.GRANT:
            if current is not None:
                return None
            states[target] = ("active", "active")
        elif intent is LifecycleAuthorityIntent.DEACTIVATE:
            if current is None or current[0] != "active":
                return None
            states[target] = ("inactive", current[1])
            if not any(status == "active" and user_status == "active"
                       for status, user_status in states.values()):
                return None
        else:
            if current is None or current[0] != "inactive":
                return None
            states[target] = ("active", current[1])
        return [(user, state[0]) for user, state in sorted(states.items())]

    def _resolve_anchor(
        self, transaction: Connection, row: Row[Any], change_id: Any,
        actor: bytes, revisions: str,
    ) -> Any:
        if (_stored(row.actor_user_id) != actor or _stored(row.target_user_id) != actor
                or row.intent != "anchor" or row.expected_revision_id is not None):
            raise LifecycleAuthoritySetConflict
        revision = _stored(row.resulting_revision_id)
        self._revision_exists(transaction, revisions, revision)
        return self._domain.anchored_type(
            change_id, self._domain.revision_type(_decode(revision))
        )

    def _resolve_change(
        self, transaction: Connection, row: Row[Any], change_id: Any,
        intent: LifecycleAuthorityIntent, parameters: dict[str, Any], revisions: str,
    ) -> Any:
        if (_stored(row.actor_user_id) != parameters["actor"]
                or _stored(row.target_user_id) != parameters["target"]
                or row.intent != intent.value
                or _stored(row.expected_revision_id) != parameters["expected"]):
            raise LifecycleAuthoritySetConflict
        revision = _stored(row.resulting_revision_id)
        self._revision_exists(transaction, revisions, revision)
        return self._domain.result_type(
            change_id, self._domain.revision_type(_decode(revision)),
            UserId(_decode(parameters["target"])), intent,
        )

    @staticmethod
    def _revision_exists(transaction: Connection, revisions: str, revision: bytes):
        if transaction.execute(text(
            f"SELECT 1 FROM {revisions} WHERE revision_id=:revision"
        ), {"revision": revision}).first() is None:
            raise LifecycleAuthoritySetUnavailable


class DatabaseUserLifecycleAuthoritySets(_LifecycleAuthoritySets):
    def __init__(self, engine: Engine, *, generate_revision_id: Callable[[], Any]):
        super().__init__(engine, _USER, generate_revision_id=generate_revision_id)

    def __repr__(self) -> str:
        return "DatabaseUserLifecycleAuthoritySets()"


class DatabaseWorkspaceLifecycleAuthoritySets(_LifecycleAuthoritySets):
    def __init__(self, engine: Engine, *, generate_revision_id: Callable[[], Any]):
        super().__init__(engine, _WORKSPACE, generate_revision_id=generate_revision_id)

    def __repr__(self) -> str:
        return "DatabaseWorkspaceLifecycleAuthoritySets()"
