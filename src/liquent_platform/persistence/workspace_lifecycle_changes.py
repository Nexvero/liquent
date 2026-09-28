"""Atomic authorized persistence of complete workspace lifecycle snapshots."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, Engine, Row, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.lifecycle import (
    AuthorizedWorkspaceLifecycleChange,
    WorkspaceLifecycleChangeId,
    WorkspaceLifecycleIntent,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    WorkspaceLifecycleChangeConflict,
    WorkspaceLifecycleChangeStoreUnavailable,
)

_SELECT_CHANGE = text(
    "SELECT * FROM workspace_lifecycle_changes WHERE change_id=:change"
)
_LOCK = text(
    "LOCK TABLE identity_users, identity_workspaces,"
    " workspace_lifecycle_management_authorities,"
    " workspace_lifecycle_revisions, workspace_lifecycle_revision_members,"
    " workspace_lifecycle_current_revision, workspace_lifecycle_changes,"
    " workspace_onboarding_management IN SHARE ROW EXCLUSIVE MODE"
)
_PERMITS = text(
    "SELECT 1 FROM identity_users AS actor"
    " JOIN workspace_lifecycle_management_authorities AS authority"
    " ON authority.user_id=actor.user_id"
    " WHERE actor.user_id=:actor AND actor.status='active'"
    " AND authority.status='active'"
)
_ACTIVE_MANAGER = text(
    "SELECT 1 FROM identity_users WHERE user_id=:manager AND status='active'"
)
_CURRENT = text(
    "SELECT revision_id FROM workspace_lifecycle_current_revision"
    " WHERE singleton_key=1"
)
_MEMBERS = text(
    "SELECT workspace_id,status FROM workspace_lifecycle_revision_members"
    " WHERE revision_id=:expected ORDER BY workspace_id"
)
_WORKSPACES = text(
    "SELECT workspace_id,status FROM identity_workspaces ORDER BY workspace_id"
)
_TARGET = text(
    "SELECT status FROM identity_workspaces WHERE workspace_id=:target"
)
_INSERT_WORKSPACE = text(
    "INSERT INTO identity_workspaces VALUES (:target,'active')"
)
_INSERT_ONBOARDING = text(
    "INSERT INTO workspace_onboarding_management"
    " (user_id,workspace_id,status) VALUES (:manager,:target,'active')"
)
_DEACTIVATE = text(
    "UPDATE identity_workspaces SET status='inactive'"
    " WHERE workspace_id=:target AND status='active'"
)
_INSERT_REVISION = text(
    "INSERT INTO workspace_lifecycle_revisions VALUES (:revision)"
)
_INSERT_MEMBER = text(
    "INSERT INTO workspace_lifecycle_revision_members"
    " VALUES (:revision,:workspace,:status)"
)
_UPDATE_CURRENT = text(
    "UPDATE workspace_lifecycle_current_revision SET revision_id=:revision"
    " WHERE singleton_key=1 AND revision_id=:expected"
)
_INSERT_CHANGE = text(
    "INSERT INTO workspace_lifecycle_changes"
    " (change_id,actor_user_id,target_workspace_id,"
    " initial_onboarding_manager_user_id,intent,expected_revision_id,"
    " resulting_revision_id) VALUES"
    " (:change,:actor,:target,:manager,:intent,:expected,:revision)"
)
_SELECT_REVISION = text(
    "SELECT 1 FROM workspace_lifecycle_revisions WHERE revision_id=:revision"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise WorkspaceLifecycleChangeStoreUnavailable
    return value.encode("utf-8")


def _stored(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
        raise WorkspaceLifecycleChangeStoreUnavailable
    return bytes(value)


def _decode(value: object) -> str:
    try:
        result = _stored(value).decode("utf-8")
    except UnicodeDecodeError:
        raise WorkspaceLifecycleChangeStoreUnavailable from None
    if not result:
        raise WorkspaceLifecycleChangeStoreUnavailable
    return result


class DatabaseAuthorizedWorkspaceLifecycleChanges:
    """Order authority, complete revision, terminal status, and retry."""

    __slots__ = ("_engine", "_generate_workspace_id", "_generate_revision_id")

    def __init__(
        self,
        engine: Engine,
        *,
        generate_workspace_id: Callable[[], WorkspaceId],
        generate_revision_id: Callable[[], WorkspaceLifecycleRevisionId],
    ) -> None:
        self._engine = engine
        self._generate_workspace_id = generate_workspace_id
        self._generate_revision_id = generate_revision_id

    def __repr__(self) -> str:
        return "DatabaseAuthorizedWorkspaceLifecycleChanges()"

    def create_workspace(
        self,
        change_id: WorkspaceLifecycleChangeId,
        principal: SessionPrincipal,
        initial_onboarding_manager_user_id: UserId,
        expected_revision: WorkspaceLifecycleRevisionId,
    ) -> AuthorizedWorkspaceLifecycleChange | None:
        return self._run(lambda: self._change(
            change_id, principal, None, initial_onboarding_manager_user_id,
            WorkspaceLifecycleIntent.CREATE, expected_revision,
        ))

    def deactivate_workspace(
        self,
        change_id: WorkspaceLifecycleChangeId,
        principal: SessionPrincipal,
        target_workspace_id: WorkspaceId,
        expected_revision: WorkspaceLifecycleRevisionId,
    ) -> AuthorizedWorkspaceLifecycleChange | None:
        return self._run(lambda: self._change(
            change_id, principal, target_workspace_id, None,
            WorkspaceLifecycleIntent.DEACTIVATE, expected_revision,
        ))

    @staticmethod
    def _run(operation: Callable[[], Any]) -> Any:
        try:
            return operation()
        except WorkspaceLifecycleChangeConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = WorkspaceLifecycleChangeConflict
        except WorkspaceLifecycleChangeStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = WorkspaceLifecycleChangeStoreUnavailable
        except Exception:
            failure = WorkspaceLifecycleChangeStoreUnavailable
        raise failure()

    def _change(
        self,
        change_id: WorkspaceLifecycleChangeId,
        principal: SessionPrincipal,
        target_workspace_id: WorkspaceId | None,
        manager_user_id: UserId | None,
        intent: WorkspaceLifecycleIntent,
        expected_revision: WorkspaceLifecycleRevisionId,
    ) -> AuthorizedWorkspaceLifecycleChange | None:
        if (
            type(change_id) is not WorkspaceLifecycleChangeId
            or type(principal) is not SessionPrincipal
            or type(intent) is not WorkspaceLifecycleIntent
            or type(expected_revision) is not WorkspaceLifecycleRevisionId
        ):
            raise WorkspaceLifecycleChangeStoreUnavailable
        parameters: dict[str, Any] = {
            "change": _encode(change_id.value),
            "actor": _encode(principal.user_id),
            "expected": _encode(expected_revision.value),
            "intent": intent.value,
            "manager": None if manager_user_id is None else _encode(manager_user_id),
        }
        if target_workspace_id is not None:
            parameters["target"] = _encode(target_workspace_id)
        with self._engine.begin() as transaction:
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                raise WorkspaceLifecycleChangeStoreUnavailable
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
            if transaction.execute(_PERMITS, parameters).first() is None:
                return None
            current = transaction.scalar(_CURRENT)
            if current is None or _stored(current) != parameters["expected"]:
                return None
            members = [
                (_stored(row.workspace_id), row.status)
                for row in transaction.execute(_MEMBERS, parameters)
            ]
            workspaces = [
                (_stored(row.workspace_id), row.status)
                for row in transaction.execute(_WORKSPACES)
            ]
            if members != workspaces:
                raise WorkspaceLifecycleChangeStoreUnavailable

            if intent is WorkspaceLifecycleIntent.CREATE:
                if transaction.execute(
                    _ACTIVE_MANAGER, parameters
                ).first() is None:
                    return None
                generated = self._generate_workspace_id()
                if type(generated) is not str or not generated:
                    raise WorkspaceLifecycleChangeStoreUnavailable
                parameters["target"] = _encode(generated)
                transaction.execute(_INSERT_WORKSPACE, parameters)
                transaction.execute(_INSERT_ONBOARDING, parameters)
                workspaces.append((parameters["target"], "active"))
                workspaces.sort()
            else:
                target = transaction.execute(_TARGET, parameters).first()
                if target is None or target.status != "active":
                    return None
                if transaction.execute(_DEACTIVATE, parameters).rowcount != 1:
                    raise WorkspaceLifecycleChangeStoreUnavailable
                workspaces = [
                    (
                        workspace,
                        "inactive" if workspace == parameters["target"] else status,
                    )
                    for workspace, status in workspaces
                ]

            revision_id = self._generate_revision_id()
            if type(revision_id) is not WorkspaceLifecycleRevisionId:
                raise WorkspaceLifecycleChangeStoreUnavailable
            revision = _encode(revision_id.value)
            transaction.execute(_INSERT_REVISION, {"revision": revision})
            for workspace, status in workspaces:
                transaction.execute(_INSERT_MEMBER, {
                    "revision": revision, "workspace": workspace, "status": status,
                })
            if transaction.execute(_UPDATE_CURRENT, {
                "revision": revision, "expected": parameters["expected"],
            }).rowcount != 1:
                raise WorkspaceLifecycleChangeStoreUnavailable
            transaction.execute(_INSERT_CHANGE, dict(parameters, revision=revision))
            return AuthorizedWorkspaceLifecycleChange(
                change_id, revision_id, WorkspaceId(_decode(parameters["target"])),
                manager_user_id, intent,
            )

    @staticmethod
    def _resolve(
        transaction: Connection,
        row: Row[Any],
        change_id: WorkspaceLifecycleChangeId,
        intent: WorkspaceLifecycleIntent,
        parameters: dict[str, Any],
    ) -> AuthorizedWorkspaceLifecycleChange:
        stored_manager = (
            None if row.initial_onboarding_manager_user_id is None
            else _stored(row.initial_onboarding_manager_user_id)
        )
        if (
            _stored(row.actor_user_id) != parameters["actor"]
            or row.intent != intent.value
            or stored_manager != parameters["manager"]
            or _stored(row.expected_revision_id) != parameters["expected"]
            or (
                "target" in parameters
                and _stored(row.target_workspace_id) != parameters["target"]
            )
        ):
            raise WorkspaceLifecycleChangeConflict
        revision = _stored(row.resulting_revision_id)
        if transaction.execute(_SELECT_REVISION, {
            "revision": revision,
        }).first() is None:
            raise WorkspaceLifecycleChangeStoreUnavailable
        return AuthorizedWorkspaceLifecycleChange(
            change_id,
            WorkspaceLifecycleRevisionId(_decode(revision)),
            WorkspaceId(_decode(row.target_workspace_id)),
            None if stored_manager is None else UserId(_decode(stored_manager)),
            intent,
        )
