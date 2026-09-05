"""Atomic regular lifecycle changes for workspace management authority."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, Engine, Row, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.membership_management import (
    AuthorizedWorkspaceMembershipAuthorityLifecycleChange,
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthorityLifecycleIntent,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipAuthorityLifecycleConflict,
    WorkspaceMembershipAuthorityLifecycleUnavailable,
)

_LOCK = text(
    "LOCK TABLE identity_users, identity_workspaces,"
    " workspace_membership_management_authorities,"
    " workspace_membership_authority_set_revisions,"
    " workspace_membership_authority_set_members,"
    " workspace_membership_authority_current_sets,"
    " workspace_membership_authority_lifecycle_changes"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_SELECT_CHANGE = text(
    "SELECT * FROM workspace_membership_authority_lifecycle_changes"
    " WHERE change_id=:change"
)
_FOUNDATION = text(
    "SELECT 1 FROM identity_users AS actor"
    " JOIN workspace_membership_management_authorities AS authority"
    " ON authority.user_id=actor.user_id"
    " JOIN identity_users AS target ON target.user_id=:target"
    " JOIN identity_workspaces AS workspace"
    " ON workspace.workspace_id=authority.workspace_id"
    " WHERE actor.user_id=:actor AND actor.status='active'"
    " AND target.status='active' AND workspace.workspace_id=:workspace"
    " AND workspace.status='active' AND authority.status='active'"
)
_CURRENT = text(
    "SELECT revision_id FROM workspace_membership_authority_current_sets"
    " WHERE workspace_id=:workspace"
)
_INVENTORY = text(
    "SELECT authority.user_id,authority.status,users.status AS user_status"
    " FROM workspace_membership_management_authorities AS authority"
    " JOIN identity_users AS users ON users.user_id=authority.user_id"
    " WHERE authority.workspace_id=:workspace ORDER BY authority.user_id"
)
_MEMBERS = text(
    "SELECT user_id,status FROM workspace_membership_authority_set_members"
    " WHERE revision_id=:expected ORDER BY user_id"
)
_INSERT_AUTHORITY = text(
    "INSERT INTO workspace_membership_management_authorities"
    " (user_id,workspace_id,status) VALUES (:target,:workspace,'active')"
)
_UPDATE_AUTHORITY = text(
    "UPDATE workspace_membership_management_authorities"
    " SET status=:result_status WHERE user_id=:target"
    " AND workspace_id=:workspace AND status=:required_status"
)
_INSERT_REVISION = text(
    "INSERT INTO workspace_membership_authority_set_revisions"
    " (revision_id,workspace_id) VALUES (:revision,:workspace)"
)
_INSERT_MEMBER = text(
    "INSERT INTO workspace_membership_authority_set_members"
    " (revision_id,user_id,status) VALUES (:revision,:user,:status)"
)
_UPDATE_CURRENT = text(
    "UPDATE workspace_membership_authority_current_sets SET revision_id=:revision"
    " WHERE workspace_id=:workspace AND revision_id=:expected"
)
_INSERT_CHANGE = text(
    "INSERT INTO workspace_membership_authority_lifecycle_changes"
    " (change_id,workspace_id,actor_user_id,target_user_id,intent,"
    " expected_revision_id,resulting_revision_id)"
    " VALUES (:change,:workspace,:actor,:target,:intent,:expected,:revision)"
)
_SELECT_REVISION = text(
    "SELECT revision_id FROM workspace_membership_authority_set_revisions"
    " WHERE revision_id=:revision AND workspace_id=:workspace"
)


def _fail() -> None:
    raise WorkspaceMembershipAuthorityLifecycleUnavailable


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        _fail()
    return value.encode("utf-8")


def _stored(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
        _fail()
    return bytes(value)


def _decode(value: object) -> str:
    try:
        decoded = _stored(value).decode("utf-8")
    except UnicodeDecodeError:
        raise WorkspaceMembershipAuthorityLifecycleUnavailable from None
    if not decoded:
        _fail()
    return decoded


class DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle:
    """Order scoped authority, expected set, transition, snapshot, and retry."""

    __slots__ = ("_engine", "_generate_revision_id")

    def __init__(
        self,
        engine: Engine,
        *,
        generate_revision_id: Callable[
            [], WorkspaceMembershipAuthoritySetRevisionId
        ],
    ) -> None:
        self._engine = engine
        self._generate_revision_id = generate_revision_id

    def __repr__(self) -> str:
        return "DatabaseAuthorizedWorkspaceMembershipAuthorityLifecycle()"

    def change_authority(
        self,
        change_id: WorkspaceMembershipAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        workspace_id: WorkspaceId,
        intent: WorkspaceMembershipAuthorityLifecycleIntent,
        expected_revision: WorkspaceMembershipAuthoritySetRevisionId,
    ) -> AuthorizedWorkspaceMembershipAuthorityLifecycleChange | None:
        try:
            return self._change(
                change_id, principal, target_user_id, workspace_id,
                intent, expected_revision,
            )
        except WorkspaceMembershipAuthorityLifecycleConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = (
                WorkspaceMembershipAuthorityLifecycleConflict
            )
        except WorkspaceMembershipAuthorityLifecycleUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = WorkspaceMembershipAuthorityLifecycleUnavailable
        except Exception:
            failure = WorkspaceMembershipAuthorityLifecycleUnavailable
        raise failure()

    def _change(
        self,
        change_id: WorkspaceMembershipAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        workspace_id: WorkspaceId,
        intent: WorkspaceMembershipAuthorityLifecycleIntent,
        expected_revision: WorkspaceMembershipAuthoritySetRevisionId,
    ) -> AuthorizedWorkspaceMembershipAuthorityLifecycleChange | None:
        if (
            type(change_id) is not WorkspaceMembershipAuthorityLifecycleChangeId
            or type(principal) is not SessionPrincipal
            or type(intent) is not WorkspaceMembershipAuthorityLifecycleIntent
            or type(expected_revision)
            is not WorkspaceMembershipAuthoritySetRevisionId
        ):
            _fail()
        parameters = {
            "change": _encode(change_id.value),
            "actor": _encode(principal.user_id),
            "target": _encode(target_user_id),
            "workspace": _encode(workspace_id),
            "intent": intent.value,
            "expected": _encode(expected_revision.value),
        }
        with self._engine.begin() as transaction:
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                _fail()
            existing = transaction.execute(_SELECT_CHANGE, parameters).first()
            if existing is not None:
                return self._resolve(
                    transaction, existing, change_id, intent, parameters
                )
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK)
                existing = transaction.execute(_SELECT_CHANGE, parameters).first()
                if existing is not None:
                    return self._resolve(
                        transaction, existing, change_id, intent, parameters
                    )
            if transaction.execute(_FOUNDATION, parameters).first() is None:
                return None
            current = transaction.execute(_CURRENT, parameters).first()
            if current is None or _stored(current.revision_id) != parameters["expected"]:
                return None
            inventory = transaction.execute(_INVENTORY, parameters).all()
            members = transaction.execute(_MEMBERS, parameters).all()
            if self._snapshot(inventory) != self._snapshot(members):
                _fail()
            changed = self._transition(inventory, parameters["target"], intent)
            if changed is None:
                return None
            revision_id = self._generate_revision_id()
            if type(revision_id) is not WorkspaceMembershipAuthoritySetRevisionId:
                _fail()
            revision = _encode(revision_id.value)
            values = dict(parameters, revision=revision)
            if intent is WorkspaceMembershipAuthorityLifecycleIntent.GRANT:
                transaction.execute(_INSERT_AUTHORITY, values)
            else:
                result_status = (
                    "inactive"
                    if intent
                    is WorkspaceMembershipAuthorityLifecycleIntent.DEACTIVATE
                    else "active"
                )
                required_status = "active" if result_status == "inactive" else "inactive"
                if transaction.execute(
                    _UPDATE_AUTHORITY,
                    dict(
                        values,
                        result_status=result_status,
                        required_status=required_status,
                    ),
                ).rowcount != 1:
                    _fail()
            transaction.execute(_INSERT_REVISION, values)
            for user, status in changed:
                transaction.execute(
                    _INSERT_MEMBER, dict(values, user=user, status=status)
                )
            if transaction.execute(_UPDATE_CURRENT, values).rowcount != 1:
                _fail()
            transaction.execute(_INSERT_CHANGE, values)
            return AuthorizedWorkspaceMembershipAuthorityLifecycleChange(
                change_id, revision_id, target_user_id, workspace_id, intent
            )

    @staticmethod
    def _snapshot(rows: list[Row[Any]]) -> list[tuple[bytes, str]]:
        snapshot = []
        for row in rows:
            if row.status not in {"active", "inactive"}:
                _fail()
            snapshot.append((_stored(row.user_id), row.status))
        return snapshot

    @staticmethod
    def _transition(
        inventory: list[Row[Any]], target: bytes,
        intent: WorkspaceMembershipAuthorityLifecycleIntent,
    ) -> list[tuple[bytes, str]] | None:
        current = {user: (status, user_status) for user, status, user_status in (
            (_stored(row.user_id), row.status, row.user_status) for row in inventory
        )}
        target_state = current.get(target)
        if intent is WorkspaceMembershipAuthorityLifecycleIntent.GRANT:
            if target_state is not None:
                return None
            current[target] = ("active", "active")
        elif intent is WorkspaceMembershipAuthorityLifecycleIntent.DEACTIVATE:
            if target_state is None or target_state[0] != "active":
                return None
            current[target] = ("inactive", target_state[1])
            if not any(
                status == "active" and user_status == "active"
                for status, user_status in current.values()
            ):
                return None
        else:
            if target_state is None or target_state[0] != "inactive":
                return None
            current[target] = ("active", target_state[1])
        return [(user, state[0]) for user, state in sorted(current.items())]

    @staticmethod
    def _resolve(
        transaction: Connection,
        row: Row[Any],
        change_id: WorkspaceMembershipAuthorityLifecycleChangeId,
        intent: WorkspaceMembershipAuthorityLifecycleIntent,
        parameters: dict[str, bytes | str],
    ) -> AuthorizedWorkspaceMembershipAuthorityLifecycleChange:
        if (
            _stored(row.workspace_id) != parameters["workspace"]
            or _stored(row.actor_user_id) != parameters["actor"]
            or _stored(row.target_user_id) != parameters["target"]
            or row.intent != intent.value
            or _stored(row.expected_revision_id) != parameters["expected"]
        ):
            raise WorkspaceMembershipAuthorityLifecycleConflict
        revision = _stored(row.resulting_revision_id)
        if transaction.execute(
            _SELECT_REVISION,
            {"revision": revision, "workspace": parameters["workspace"]},
        ).first() is None:
            _fail()
        return AuthorizedWorkspaceMembershipAuthorityLifecycleChange(
            change_id,
            WorkspaceMembershipAuthoritySetRevisionId(_decode(revision)),
            UserId(_decode(parameters["target"])),
            WorkspaceId(_decode(parameters["workspace"])),
            intent,
        )
