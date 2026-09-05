"""Atomic authorized persistence of complete workspace membership snapshots."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, Engine, Row, text
from sqlalchemy.exc import IntegrityError

from liquent_platform.identity.access import MembershipStatus, Permission, UserId
from liquent_platform.identity.membership_management import (
    AuthorizedWorkspaceMembershipChange,
    WorkspaceMembershipChangeId,
    WorkspaceMembershipRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipChangeConflict,
    WorkspaceMembershipChangeStoreUnavailable,
)

_SELECT_CHANGE = text(
    "SELECT * FROM authorized_workspace_membership_changes WHERE change_id=:change"
)
_LOCK_POSTGRES = text(
    "LOCK TABLE authorized_workspace_membership_changes, workspace_memberships,"
    " workspace_membership_permissions, workspace_membership_revisions,"
    " workspace_membership_revision_permissions"
    " IN SHARE ROW EXCLUSIVE MODE"
)
_PERMITS = text(
    "SELECT 1 FROM identity_users AS actor"
    " JOIN workspace_membership_management_authorities AS authority"
    " ON authority.user_id=actor.user_id"
    " JOIN identity_users AS target ON target.user_id=:target"
    " JOIN identity_workspaces AS workspace"
    " ON workspace.workspace_id=authority.workspace_id"
    " WHERE actor.user_id=:actor AND workspace.workspace_id=:workspace"
    " AND actor.status='active' AND target.status='active'"
    " AND workspace.status='active' AND authority.status='active'"
)
_PERMITS_POSTGRES = text(str(_PERMITS) + " FOR UPDATE OF actor,target,workspace,authority")
_CURRENT = text(
    "SELECT revision_id FROM workspace_memberships"
    " WHERE user_id=:target AND workspace_id=:workspace"
)
_CURRENT_POSTGRES = text(str(_CURRENT) + " FOR UPDATE")
_INSERT_REVISION = text(
    "INSERT INTO workspace_membership_revisions"
    " (revision_id,user_id,workspace_id,status)"
    " VALUES (:revision,:target,:workspace,:status)"
)
_INSERT_REVISION_PERMISSION = text(
    "INSERT INTO workspace_membership_revision_permissions"
    " (revision_id,permission) VALUES (:revision,:permission)"
)
_UPSERT_MEMBERSHIP = text(
    "INSERT INTO workspace_memberships"
    " (user_id,workspace_id,status,revision_id)"
    " VALUES (:target,:workspace,:status,:revision)"
    " ON CONFLICT (user_id,workspace_id) DO UPDATE SET"
    " status=excluded.status,revision_id=excluded.revision_id"
)
_DELETE_PERMISSIONS = text(
    "DELETE FROM workspace_membership_permissions"
    " WHERE user_id=:target AND workspace_id=:workspace"
)
_INSERT_PERMISSION = text(
    "INSERT INTO workspace_membership_permissions"
    " (user_id,workspace_id,permission)"
    " VALUES (:target,:workspace,:permission)"
)
_INSERT_CHANGE = text(
    "INSERT INTO authorized_workspace_membership_changes"
    " (change_id,actor_user_id,target_user_id,workspace_id,"
    " expected_revision_id,resulting_revision_id)"
    " VALUES (:change,:actor,:target,:workspace,:expected,:resulting)"
)
_SELECT_REVISION = text(
    "SELECT * FROM workspace_membership_revisions WHERE revision_id=:revision"
)
_SELECT_REVISION_PERMISSIONS = text(
    "SELECT permission FROM workspace_membership_revision_permissions"
    " WHERE revision_id=:revision ORDER BY permission"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise WorkspaceMembershipChangeStoreUnavailable
    return value.encode("utf-8")


def _stored(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
        raise WorkspaceMembershipChangeStoreUnavailable
    return bytes(value)


def _decode(value: object) -> str:
    try:
        decoded = _stored(value).decode("utf-8")
    except UnicodeDecodeError:
        raise WorkspaceMembershipChangeStoreUnavailable from None
    if not decoded:
        raise WorkspaceMembershipChangeStoreUnavailable
    return decoded


def _validate_snapshot(
    status: MembershipStatus, permissions: frozenset[Permission]
) -> None:
    if type(status) is not MembershipStatus or type(permissions) is not frozenset:
        raise WorkspaceMembershipChangeStoreUnavailable
    if any(type(permission) is not Permission for permission in permissions):
        raise WorkspaceMembershipChangeStoreUnavailable
    if status is MembershipStatus.INACTIVE and permissions:
        raise WorkspaceMembershipChangeStoreUnavailable


class DatabaseAuthorizedWorkspaceMembershipChanges:
    """Order current authority, revision, snapshot, and retry decision."""

    __slots__ = ("_engine", "_generate_revision_id")

    def __init__(
        self,
        engine: Engine,
        *,
        generate_revision_id: Callable[[], WorkspaceMembershipRevisionId],
    ) -> None:
        self._engine = engine
        self._generate_revision_id = generate_revision_id

    def __repr__(self) -> str:
        return "DatabaseAuthorizedWorkspaceMembershipChanges()"

    def change_membership(
        self,
        change_id: WorkspaceMembershipChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        workspace_id: WorkspaceId,
        expected_revision: WorkspaceMembershipRevisionId | None,
        status: MembershipStatus,
        permissions: frozenset[Permission],
    ) -> AuthorizedWorkspaceMembershipChange | None:
        try:
            return self._change(
                change_id, principal, target_user_id, workspace_id,
                expected_revision, status, permissions,
            )
        except WorkspaceMembershipChangeConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = WorkspaceMembershipChangeConflict
        except WorkspaceMembershipChangeStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = WorkspaceMembershipChangeStoreUnavailable
        except Exception:
            failure = WorkspaceMembershipChangeStoreUnavailable
        raise failure()

    def _change(
        self,
        change_id: WorkspaceMembershipChangeId,
        principal: SessionPrincipal,
        target_user_id: UserId,
        workspace_id: WorkspaceId,
        expected_revision: WorkspaceMembershipRevisionId | None,
        status: MembershipStatus,
        permissions: frozenset[Permission],
    ) -> AuthorizedWorkspaceMembershipChange | None:
        _validate_snapshot(status, permissions)
        change = _encode(change_id.value)
        actor = _encode(principal.user_id)
        target = _encode(target_user_id)
        workspace = _encode(workspace_id)
        expected = (
            None if expected_revision is None else _encode(expected_revision.value)
        )
        parameters = {
            "change": change, "actor": actor, "target": target,
            "workspace": workspace, "expected": expected,
        }
        with self._engine.begin() as transaction:
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                raise WorkspaceMembershipChangeStoreUnavailable
            existing = transaction.execute(_SELECT_CHANGE, parameters).first()
            if existing is not None:
                return self._resolve(
                    transaction, existing, change_id, actor, target, workspace,
                    expected, status, permissions,
                )
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK_POSTGRES)
                existing = transaction.execute(_SELECT_CHANGE, parameters).first()
                if existing is not None:
                    return self._resolve(
                        transaction, existing, change_id, actor, target, workspace,
                        expected, status, permissions,
                    )
            permits = (
                _PERMITS_POSTGRES
                if transaction.dialect.name == "postgresql"
                else _PERMITS
            )
            if transaction.execute(permits, parameters).first() is None:
                return None
            current_query = (
                _CURRENT_POSTGRES
                if transaction.dialect.name == "postgresql"
                else _CURRENT
            )
            current = transaction.execute(current_query, parameters).first()
            if expected is None:
                if current is not None:
                    return None
            elif current is None or current.revision_id is None or (
                _stored(current.revision_id) != expected
            ):
                return None

            revision_id = self._generate_revision_id()
            if type(revision_id) is not WorkspaceMembershipRevisionId:
                raise WorkspaceMembershipChangeStoreUnavailable
            revision = _encode(revision_id.value)
            snapshot = dict(parameters, revision=revision, status=status.value)
            transaction.execute(_INSERT_REVISION, snapshot)
            for permission in sorted(permissions, key=lambda item: item.value):
                transaction.execute(
                    _INSERT_REVISION_PERMISSION,
                    {"revision": revision, "permission": permission.value},
                )
            transaction.execute(_UPSERT_MEMBERSHIP, snapshot)
            transaction.execute(_DELETE_PERMISSIONS, parameters)
            for permission in sorted(permissions, key=lambda item: item.value):
                transaction.execute(
                    _INSERT_PERMISSION,
                    dict(parameters, permission=permission.value),
                )
            try:
                transaction.execute(
                    _INSERT_CHANGE, dict(parameters, resulting=revision)
                )
            except IntegrityError:
                raise WorkspaceMembershipChangeStoreUnavailable from None
            return AuthorizedWorkspaceMembershipChange(
                change_id, revision_id, target_user_id, workspace_id,
                status, permissions,
            )

    @staticmethod
    def _resolve(
        transaction: Connection,
        row: Row[Any],
        change_id: WorkspaceMembershipChangeId,
        actor: bytes,
        target: bytes,
        workspace: bytes,
        expected: bytes | None,
        status: MembershipStatus,
        permissions: frozenset[Permission],
    ) -> AuthorizedWorkspaceMembershipChange:
        stored_expected = (
            None if row.expected_revision_id is None
            else _stored(row.expected_revision_id)
        )
        if (
            _stored(row.actor_user_id) != actor
            or _stored(row.target_user_id) != target
            or _stored(row.workspace_id) != workspace
            or stored_expected != expected
        ):
            raise WorkspaceMembershipChangeConflict
        revision = _stored(row.resulting_revision_id)
        snapshot = transaction.execute(
            _SELECT_REVISION, {"revision": revision}
        ).first()
        if snapshot is None:
            raise WorkspaceMembershipChangeStoreUnavailable
        try:
            stored_status = MembershipStatus(snapshot.status)
            stored_permissions = frozenset(
                Permission(item.permission)
                for item in transaction.execute(
                    _SELECT_REVISION_PERMISSIONS, {"revision": revision}
                )
            )
        except (TypeError, ValueError):
            raise WorkspaceMembershipChangeStoreUnavailable from None
        if (
            _stored(snapshot.user_id) != target
            or _stored(snapshot.workspace_id) != workspace
            or stored_status is not status
            or stored_permissions != permissions
        ):
            raise WorkspaceMembershipChangeConflict
        return AuthorizedWorkspaceMembershipChange(
            change_id,
            WorkspaceMembershipRevisionId(_decode(revision)),
            UserId(_decode(target)),
            WorkspaceId(_decode(workspace)),
            status,
            permissions,
        )
