"""Offline recovery of historical workspace membership-management authority."""

from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, Engine, Row, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.membership_management import (
    RecoveredWorkspaceMembershipAuthoritySet,
    WorkspaceMembershipAuthorityRecoveryId,
    WorkspaceMembershipAuthoritySetRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.identity_errors import (
    WorkspaceMembershipAuthorityRecoveryConflict,
    WorkspaceMembershipAuthorityRecoveryUnavailable,
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
_SELECT_RECOVERY = text(
    "SELECT * FROM workspace_membership_authority_recoveries"
    " WHERE recovery_id=:recovery"
)
_TARGET = text(
    "SELECT 1 FROM identity_users AS users"
    " JOIN workspace_membership_management_authorities AS authority"
    " ON authority.user_id=users.user_id"
    " JOIN identity_workspaces AS workspace"
    " ON workspace.workspace_id=authority.workspace_id"
    " WHERE users.user_id=:target AND users.status='active'"
    " AND workspace.workspace_id=:workspace AND workspace.status='active'"
    " AND authority.status='inactive'"
)
_CURRENT = text(
    "SELECT revision_id FROM workspace_membership_authority_current_sets"
    " WHERE workspace_id=:workspace"
)
_TERMINAL = text(
    "SELECT"
    " ((SELECT count(*) FROM workspace_membership_authority_lifecycle_changes"
    " WHERE workspace_id=:workspace AND resulting_revision_id=:expected) +"
    " (SELECT count(*) FROM workspace_membership_authority_recoveries"
    " WHERE workspace_id=:workspace AND resulting_revision_id=:expected)) AS origins,"
    " ((SELECT count(*) FROM workspace_membership_authority_lifecycle_changes"
    " WHERE workspace_id=:workspace AND expected_revision_id=:expected) +"
    " (SELECT count(*) FROM workspace_membership_authority_recoveries"
    " WHERE workspace_id=:workspace AND expected_revision_id=:expected)) AS successors"
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
_REACTIVATE = text(
    "UPDATE workspace_membership_management_authorities SET status='active'"
    " WHERE user_id=:target AND workspace_id=:workspace AND status='inactive'"
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
_INSERT_CURRENT = text(
    "INSERT INTO workspace_membership_authority_current_sets"
    " (workspace_id,revision_id) VALUES (:workspace,:revision)"
)
_INSERT_RECOVERY = text(
    "INSERT INTO workspace_membership_authority_recoveries"
    " (recovery_id,workspace_id,target_user_id,expected_revision_id,"
    " resulting_revision_id)"
    " VALUES (:recovery,:workspace,:target,:expected,:revision)"
)
_SELECT_REVISION = text(
    "SELECT revision_id FROM workspace_membership_authority_set_revisions"
    " WHERE revision_id=:revision AND workspace_id=:workspace"
)


def _fail() -> None:
    raise WorkspaceMembershipAuthorityRecoveryUnavailable


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
        raise WorkspaceMembershipAuthorityRecoveryUnavailable from None
    if not decoded:
        _fail()
    return decoded


class DatabaseOfflineWorkspaceMembershipAuthorityRecovery:
    """Reactivate only eligible historical authority in a closed workspace."""

    __slots__ = ("_engine", "_generate_revision_id")

    def __init__(
        self, engine: Engine, *,
        generate_revision_id: Callable[
            [], WorkspaceMembershipAuthoritySetRevisionId
        ],
    ) -> None:
        self._engine = engine
        self._generate_revision_id = generate_revision_id

    def __repr__(self) -> str:
        return "DatabaseOfflineWorkspaceMembershipAuthorityRecovery()"

    def recover(
        self,
        recovery_id: WorkspaceMembershipAuthorityRecoveryId,
        target_user_id: UserId,
        workspace_id: WorkspaceId,
        expected_revision: WorkspaceMembershipAuthoritySetRevisionId,
    ) -> RecoveredWorkspaceMembershipAuthoritySet | None:
        try:
            return self._recover(
                recovery_id, target_user_id, workspace_id, expected_revision
            )
        except WorkspaceMembershipAuthorityRecoveryConflict as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure: type[Exception] = WorkspaceMembershipAuthorityRecoveryConflict
        except WorkspaceMembershipAuthorityRecoveryUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
            failure = WorkspaceMembershipAuthorityRecoveryUnavailable
        except Exception:
            failure = WorkspaceMembershipAuthorityRecoveryUnavailable
        raise failure()

    def _recover(
        self,
        recovery_id: WorkspaceMembershipAuthorityRecoveryId,
        target_user_id: UserId,
        workspace_id: WorkspaceId,
        expected_revision: WorkspaceMembershipAuthoritySetRevisionId,
    ) -> RecoveredWorkspaceMembershipAuthoritySet | None:
        if (
            type(recovery_id) is not WorkspaceMembershipAuthorityRecoveryId
            or type(expected_revision)
            is not WorkspaceMembershipAuthoritySetRevisionId
        ):
            _fail()
        parameters = {
            "recovery": _encode(recovery_id.value),
            "target": _encode(target_user_id),
            "workspace": _encode(workspace_id),
            "expected": _encode(expected_revision.value),
        }
        with self._engine.begin() as transaction:
            if transaction.dialect.name not in {"postgresql", "sqlite"}:
                _fail()
            existing = transaction.execute(_SELECT_RECOVERY, parameters).first()
            if existing is not None:
                return self._resolve(transaction, existing, recovery_id, parameters)
            if transaction.dialect.name == "postgresql":
                transaction.execute(_LOCK)
                existing = transaction.execute(
                    _SELECT_RECOVERY, parameters
                ).first()
                if existing is not None:
                    return self._resolve(
                        transaction, existing, recovery_id, parameters
                    )
            if transaction.execute(_TARGET, parameters).first() is None:
                return None
            current = transaction.execute(_CURRENT, parameters).first()
            has_current = current is not None
            if has_current:
                if _stored(current.revision_id) != parameters["expected"]:
                    return None
            else:
                terminal = transaction.execute(_TERMINAL, parameters).one()
                if terminal.origins != 1 or terminal.successors != 0:
                    return None
            inventory = transaction.execute(_INVENTORY, parameters).all()
            members = transaction.execute(_MEMBERS, parameters).all()
            snapshot = self._snapshot(inventory)
            if snapshot != self._snapshot(members):
                _fail()
            if any(
                row.status == "active" and row.user_status == "active"
                for row in inventory
            ):
                return None
            changed = [
                (user, "active" if user == parameters["target"] else status)
                for user, status in snapshot
            ]
            if transaction.execute(_REACTIVATE, parameters).rowcount != 1:
                _fail()
            revision_id = self._generate_revision_id()
            if type(revision_id) is not WorkspaceMembershipAuthoritySetRevisionId:
                _fail()
            revision = _encode(revision_id.value)
            values = dict(parameters, revision=revision)
            transaction.execute(_INSERT_REVISION, values)
            for user, status in changed:
                transaction.execute(
                    _INSERT_MEMBER, dict(values, user=user, status=status)
                )
            if has_current:
                if transaction.execute(_UPDATE_CURRENT, values).rowcount != 1:
                    _fail()
            else:
                transaction.execute(_INSERT_CURRENT, values)
            transaction.execute(_INSERT_RECOVERY, values)
            return RecoveredWorkspaceMembershipAuthoritySet(
                recovery_id, revision_id, target_user_id, workspace_id
            )

    @staticmethod
    def _snapshot(rows: list[Row[Any]]) -> list[tuple[bytes, str]]:
        result = []
        for row in rows:
            if row.status not in {"active", "inactive"}:
                _fail()
            result.append((_stored(row.user_id), row.status))
        return result

    @staticmethod
    def _resolve(
        transaction: Connection, row: Row[Any],
        recovery_id: WorkspaceMembershipAuthorityRecoveryId,
        parameters: dict[str, bytes],
    ) -> RecoveredWorkspaceMembershipAuthoritySet:
        if (
            _stored(row.workspace_id) != parameters["workspace"]
            or _stored(row.target_user_id) != parameters["target"]
            or _stored(row.expected_revision_id) != parameters["expected"]
        ):
            raise WorkspaceMembershipAuthorityRecoveryConflict
        revision = _stored(row.resulting_revision_id)
        if transaction.execute(
            _SELECT_REVISION,
            {"revision": revision, "workspace": parameters["workspace"]},
        ).first() is None:
            _fail()
        return RecoveredWorkspaceMembershipAuthoritySet(
            recovery_id,
            WorkspaceMembershipAuthoritySetRevisionId(_decode(revision)),
            UserId(_decode(parameters["target"])),
            WorkspaceId(_decode(parameters["workspace"])),
        )
