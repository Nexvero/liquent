"""Controlled anchoring of existing workspace management authority."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, Engine, Row, text

from liquent_platform.identity.membership_management import (
    AnchoredWorkspaceMembershipAuthoritySet,
    WorkspaceMembershipAuthorityLifecycleChangeId,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipAuthorityAnchorConflict,
    WorkspaceMembershipAuthorityAnchorUnavailable,
)

_LOCK = text(
    "LOCK TABLE identity_users, identity_workspaces,"
    " workspace_membership_management_authorities,"
    " workspace_membership_authority_set_revisions,"
    " workspace_membership_authority_set_members,"
    " workspace_membership_authority_current_sets,"
    " workspace_membership_authority_lifecycle_changes,"
    " workspace_membership_authority_recoveries IN SHARE ROW EXCLUSIVE MODE"
)
_SELECT_CHANGE = text(
    "SELECT * FROM workspace_membership_authority_lifecycle_changes"
    " WHERE change_id=:change"
)
_EMPTY = text(
    "SELECT NOT EXISTS (SELECT 1 FROM workspace_membership_authority_set_revisions"
    " WHERE workspace_id=:workspace)"
    " AND NOT EXISTS (SELECT 1 FROM workspace_membership_authority_current_sets"
    " WHERE workspace_id=:workspace)"
    " AND NOT EXISTS (SELECT 1 FROM workspace_membership_authority_lifecycle_changes"
    " WHERE workspace_id=:workspace)"
    " AND NOT EXISTS (SELECT 1 FROM workspace_membership_authority_recoveries"
    " WHERE workspace_id=:workspace)"
)
_ACTOR = text(
    "SELECT 1 FROM identity_users AS users"
    " JOIN workspace_membership_management_authorities AS authority"
    " ON authority.user_id=users.user_id"
    " JOIN identity_workspaces AS workspace"
    " ON workspace.workspace_id=authority.workspace_id"
    " WHERE users.user_id=:actor AND users.status='active'"
    " AND workspace.workspace_id=:workspace AND workspace.status='active'"
    " AND authority.status='active'"
)
_INVENTORY = text(
    "SELECT authority.user_id,authority.status"
    " FROM workspace_membership_management_authorities AS authority"
    " JOIN identity_users AS users ON users.user_id=authority.user_id"
    " WHERE authority.workspace_id=:workspace ORDER BY authority.user_id"
)
_INSERT_REVISION = text(
    "INSERT INTO workspace_membership_authority_set_revisions"
    " (revision_id,workspace_id) VALUES (:revision,:workspace)"
)
_INSERT_MEMBER = text(
    "INSERT INTO workspace_membership_authority_set_members"
    " (revision_id,user_id,status) VALUES (:revision,:user,:status)"
)
_INSERT_CURRENT = text(
    "INSERT INTO workspace_membership_authority_current_sets"
    " (workspace_id,revision_id) VALUES (:workspace,:revision)"
)
_INSERT_CHANGE = text(
    "INSERT INTO workspace_membership_authority_lifecycle_changes"
    " (change_id,workspace_id,actor_user_id,target_user_id,intent,"
    " expected_revision_id,resulting_revision_id)"
    " VALUES (:change,:workspace,:actor,:actor,'anchor',NULL,:revision)"
)
_SELECT_REVISION = text(
    "SELECT revision_id FROM workspace_membership_authority_set_revisions"
    " WHERE revision_id=:revision AND workspace_id=:workspace"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise WorkspaceMembershipAuthorityAnchorUnavailable
    return value.encode("utf-8")


def _stored(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
        raise WorkspaceMembershipAuthorityAnchorUnavailable
    return bytes(value)


def _decode(value: object) -> str:
    try:
        decoded = _stored(value).decode("utf-8")
    except UnicodeDecodeError:
        raise WorkspaceMembershipAuthorityAnchorUnavailable from None
    if not decoded:
        raise WorkspaceMembershipAuthorityAnchorUnavailable
    return decoded


class DatabaseWorkspaceMembershipAuthoritySetAnchor:
    """Create one workspace's first set revision from bootstrap facts."""

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
        return "DatabaseWorkspaceMembershipAuthoritySetAnchor()"

    def anchor(
        self,
        change_id: WorkspaceMembershipAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
        workspace_id: WorkspaceId,
    ) -> AnchoredWorkspaceMembershipAuthoritySet | None:
        try:
            return self._anchor(change_id, principal, workspace_id)
        except WorkspaceMembershipAuthorityAnchorConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = WorkspaceMembershipAuthorityAnchorConflict
        except WorkspaceMembershipAuthorityAnchorUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = WorkspaceMembershipAuthorityAnchorUnavailable
        except Exception:
            failure = WorkspaceMembershipAuthorityAnchorUnavailable
        raise failure()

    def _anchor(
        self,
        change_id: WorkspaceMembershipAuthorityLifecycleChangeId,
        principal: SessionPrincipal,
        workspace_id: WorkspaceId,
    ) -> AnchoredWorkspaceMembershipAuthoritySet | None:
        if type(change_id) is not WorkspaceMembershipAuthorityLifecycleChangeId:
            raise WorkspaceMembershipAuthorityAnchorUnavailable
        if type(principal) is not SessionPrincipal:
            raise WorkspaceMembershipAuthorityAnchorUnavailable
        parameters = {
            "change": _encode(change_id.value),
            "actor": _encode(principal.user_id),
            "workspace": _encode(workspace_id),
        }
        with self._engine.begin() as transaction:
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                raise WorkspaceMembershipAuthorityAnchorUnavailable
            existing = transaction.execute(_SELECT_CHANGE, parameters).first()
            if existing is not None:
                return self._resolve(
                    transaction, existing, change_id, workspace_id, parameters
                )
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK)
                existing = transaction.execute(_SELECT_CHANGE, parameters).first()
                if existing is not None:
                    return self._resolve(
                        transaction, existing, change_id, workspace_id, parameters
                    )
            if not transaction.scalar(_EMPTY, parameters):
                return None
            if transaction.execute(_ACTOR, parameters).first() is None:
                return None
            inventory = transaction.execute(_INVENTORY, parameters).all()
            if not inventory:
                return None
            revision_id = self._generate_revision_id()
            if type(revision_id) is not WorkspaceMembershipAuthoritySetRevisionId:
                raise WorkspaceMembershipAuthorityAnchorUnavailable
            revision = _encode(revision_id.value)
            values = dict(parameters, revision=revision)
            transaction.execute(_INSERT_REVISION, values)
            for member in inventory:
                transaction.execute(
                    _INSERT_MEMBER,
                    dict(
                        values,
                        user=_stored(member.user_id),
                        status=member.status,
                    ),
                )
            transaction.execute(_INSERT_CURRENT, values)
            transaction.execute(_INSERT_CHANGE, values)
            return AnchoredWorkspaceMembershipAuthoritySet(
                change_id, revision_id, workspace_id
            )

    @staticmethod
    def _resolve(
        transaction: Connection,
        row: Row[Any],
        change_id: WorkspaceMembershipAuthorityLifecycleChangeId,
        workspace_id: WorkspaceId,
        parameters: dict[str, bytes],
    ) -> AnchoredWorkspaceMembershipAuthoritySet:
        if (
            _stored(row.workspace_id) != parameters["workspace"]
            or _stored(row.actor_user_id) != parameters["actor"]
            or _stored(row.target_user_id) != parameters["actor"]
            or row.intent != "anchor"
            or row.expected_revision_id is not None
        ):
            raise WorkspaceMembershipAuthorityAnchorConflict
        revision = _stored(row.resulting_revision_id)
        if transaction.execute(
            _SELECT_REVISION,
            {"revision": revision, "workspace": parameters["workspace"]},
        ).first() is None:
            raise WorkspaceMembershipAuthorityAnchorUnavailable
        return AnchoredWorkspaceMembershipAuthoritySet(
            change_id,
            WorkspaceMembershipAuthoritySetRevisionId(_decode(revision)),
            workspace_id,
        )
