"""Controlled one-time anchoring of a canonical initial identity inventory."""

from collections.abc import Callable

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.lifecycle import (
    AnchoredIdentityLifecycleFoundation,
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.identity_errors import (
    IdentityLifecycleFoundationAnchorUnavailable,
)

_LOCK = text(
    "LOCK TABLE identity_users, identity_workspaces,"
    " workspace_onboarding_management, user_lifecycle_management_authorities,"
    " workspace_lifecycle_management_authorities, user_lifecycle_revisions,"
    " user_lifecycle_revision_members, user_lifecycle_current_revision,"
    " user_lifecycle_changes, workspace_lifecycle_revisions,"
    " workspace_lifecycle_revision_members, workspace_lifecycle_current_revision,"
    " workspace_lifecycle_changes IN SHARE ROW EXCLUSIVE MODE"
)
_COUNTS = text(
    "SELECT (SELECT count(*) FROM identity_users),"
    " (SELECT count(*) FROM identity_workspaces),"
    " (SELECT count(*) FROM workspace_onboarding_management),"
    " (SELECT count(*) FROM user_lifecycle_management_authorities),"
    " (SELECT count(*) FROM workspace_lifecycle_management_authorities),"
    " (SELECT count(*) FROM user_lifecycle_revisions),"
    " (SELECT count(*) FROM user_lifecycle_revision_members),"
    " (SELECT count(*) FROM user_lifecycle_current_revision),"
    " (SELECT count(*) FROM user_lifecycle_changes),"
    " (SELECT count(*) FROM workspace_lifecycle_revisions),"
    " (SELECT count(*) FROM workspace_lifecycle_revision_members),"
    " (SELECT count(*) FROM workspace_lifecycle_current_revision),"
    " (SELECT count(*) FROM workspace_lifecycle_changes)"
)
_CANONICAL = text(
    "SELECT users.user_id,workspaces.workspace_id"
    " FROM identity_users AS users"
    " JOIN workspace_onboarding_management AS authority"
    " ON authority.user_id=users.user_id"
    " JOIN identity_workspaces AS workspaces"
    " ON workspaces.workspace_id=authority.workspace_id"
    " WHERE users.status='active' AND workspaces.status='active'"
    " AND authority.status='active'"
)
_INSERT_USER_AUTHORITY = text(
    "INSERT INTO user_lifecycle_management_authorities VALUES (:user,'active')"
)
_INSERT_WORKSPACE_AUTHORITY = text(
    "INSERT INTO workspace_lifecycle_management_authorities VALUES (:user,'active')"
)
_INSERT_USER_REVISION = text(
    "INSERT INTO user_lifecycle_revisions VALUES (:revision)"
)
_INSERT_USER_MEMBER = text(
    "INSERT INTO user_lifecycle_revision_members VALUES (:revision,:user,'active')"
)
_INSERT_USER_CURRENT = text(
    "INSERT INTO user_lifecycle_current_revision VALUES (1,:revision)"
)
_INSERT_WORKSPACE_REVISION = text(
    "INSERT INTO workspace_lifecycle_revisions VALUES (:revision)"
)
_INSERT_WORKSPACE_MEMBER = text(
    "INSERT INTO workspace_lifecycle_revision_members"
    " VALUES (:revision,:workspace,'active')"
)
_INSERT_WORKSPACE_CURRENT = text(
    "INSERT INTO workspace_lifecycle_current_revision VALUES (1,:revision)"
)


def _stored(value: object) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)) or not value:
        raise IdentityLifecycleFoundationAnchorUnavailable
    return bytes(value)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise IdentityLifecycleFoundationAnchorUnavailable
    return value.encode("utf-8")


def _decode(value: object) -> str:
    try:
        result = _stored(value).decode("utf-8")
    except UnicodeDecodeError:
        raise IdentityLifecycleFoundationAnchorUnavailable from None
    if not result:
        raise IdentityLifecycleFoundationAnchorUnavailable
    return result


class DatabaseInitialIdentityLifecycleFoundationAnchor:
    """Adopt only one exact active pre-LQ-220 bootstrap foundation."""

    __slots__ = (
        "_engine",
        "_generate_user_revision_id",
        "_generate_workspace_revision_id",
    )

    def __init__(
        self,
        engine: Engine,
        *,
        generate_user_revision_id: Callable[[], UserLifecycleRevisionId],
        generate_workspace_revision_id: Callable[[], WorkspaceLifecycleRevisionId],
    ) -> None:
        self._engine = engine
        self._generate_user_revision_id = generate_user_revision_id
        self._generate_workspace_revision_id = generate_workspace_revision_id

    def __repr__(self) -> str:
        return "DatabaseInitialIdentityLifecycleFoundationAnchor()"

    def anchor(self) -> AnchoredIdentityLifecycleFoundation | None:
        try:
            with self._engine.begin() as transaction:
                return self._anchor(transaction)
        except IdentityLifecycleFoundationAnchorUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise IdentityLifecycleFoundationAnchorUnavailable

    def _anchor(
        self, transaction: Connection
    ) -> AnchoredIdentityLifecycleFoundation | None:
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK)
        elif transaction.dialect.name != "sqlite":
            raise IdentityLifecycleFoundationAnchorUnavailable

        if transaction.execute(_COUNTS).one() != (
            1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        ):
            return None
        row = transaction.execute(_CANONICAL).first()
        if row is None:
            return None
        user = _stored(row.user_id)
        workspace = _stored(row.workspace_id)
        user_revision_id = self._generate_user_revision_id()
        workspace_revision_id = self._generate_workspace_revision_id()
        if type(user_revision_id) is not UserLifecycleRevisionId:
            raise IdentityLifecycleFoundationAnchorUnavailable
        if type(workspace_revision_id) is not WorkspaceLifecycleRevisionId:
            raise IdentityLifecycleFoundationAnchorUnavailable
        user_revision = _encode(user_revision_id.value)
        workspace_revision = _encode(workspace_revision_id.value)

        transaction.execute(_INSERT_USER_AUTHORITY, {"user": user})
        transaction.execute(_INSERT_WORKSPACE_AUTHORITY, {"user": user})
        transaction.execute(_INSERT_USER_REVISION, {"revision": user_revision})
        transaction.execute(
            _INSERT_USER_MEMBER, {"revision": user_revision, "user": user}
        )
        transaction.execute(_INSERT_USER_CURRENT, {"revision": user_revision})
        transaction.execute(
            _INSERT_WORKSPACE_REVISION, {"revision": workspace_revision}
        )
        transaction.execute(
            _INSERT_WORKSPACE_MEMBER,
            {"revision": workspace_revision, "workspace": workspace},
        )
        transaction.execute(
            _INSERT_WORKSPACE_CURRENT, {"revision": workspace_revision}
        )
        return AnchoredIdentityLifecycleFoundation(
            UserId(_decode(user)),
            WorkspaceId(_decode(workspace)),
            user_revision_id,
            workspace_revision_id,
        )
