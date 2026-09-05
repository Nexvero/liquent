"""One-time atomic bootstrap of the persistent identity authority foundation."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Connection, Engine, text

from liquent_platform.identity.access import (
    BootstrappedIdentityAuthority,
    UserId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.lifecycle import (
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.persistence.identity_errors import (
    IdentityAuthorityBootstrapUnavailable,
)

_LOCK_FOUNDATION = text(
    "LOCK TABLE identity_users, identity_workspaces,"
    " workspace_onboarding_management, user_lifecycle_management_authorities,"
    " workspace_lifecycle_management_authorities, user_lifecycle_revisions,"
    " user_lifecycle_revision_members, user_lifecycle_current_revision,"
    " workspace_lifecycle_revisions, workspace_lifecycle_revision_members,"
    " workspace_lifecycle_current_revision IN SHARE ROW EXCLUSIVE MODE"
)
_HAS_INVENTORY = text(
    "SELECT EXISTS (SELECT 1 FROM identity_users)"
    " OR EXISTS (SELECT 1 FROM identity_workspaces)"
    " OR EXISTS (SELECT 1 FROM workspace_onboarding_management)"
    " OR EXISTS (SELECT 1 FROM user_lifecycle_management_authorities)"
    " OR EXISTS (SELECT 1 FROM workspace_lifecycle_management_authorities)"
    " OR EXISTS (SELECT 1 FROM user_lifecycle_revisions)"
    " OR EXISTS (SELECT 1 FROM workspace_lifecycle_revisions)"
)
_INSERT_USER = text(
    "INSERT INTO identity_users (user_id, status) VALUES (:user, 'active')"
)
_INSERT_WORKSPACE = text(
    "INSERT INTO identity_workspaces (workspace_id, status)"
    " VALUES (:workspace, 'active')"
)
_INSERT_AUTHORITY = text(
    "INSERT INTO workspace_onboarding_management (user_id, workspace_id, status)"
    " VALUES (:user, :workspace, 'active')"
)
_INSERT_USER_LIFECYCLE_AUTHORITY = text(
    "INSERT INTO user_lifecycle_management_authorities VALUES (:user,'active')"
)
_INSERT_WORKSPACE_LIFECYCLE_AUTHORITY = text(
    "INSERT INTO workspace_lifecycle_management_authorities"
    " VALUES (:user,'active')"
)
_INSERT_USER_REVISION = text(
    "INSERT INTO user_lifecycle_revisions VALUES (:revision)"
)
_INSERT_USER_MEMBER = text(
    "INSERT INTO user_lifecycle_revision_members"
    " VALUES (:revision,:user,'active')"
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


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise IdentityAuthorityBootstrapUnavailable
    return value.encode("utf-8")


class DatabaseInitialIdentityAuthorityBootstrap:
    """Create the first three foundation facts, once, under database locking."""

    __slots__ = (
        "_engine",
        "_generate_user_id",
        "_generate_workspace_id",
        "_generate_user_revision_id",
        "_generate_workspace_revision_id",
    )

    def __init__(
        self,
        engine: Engine,
        *,
        generate_user_id: Callable[[], UserId],
        generate_workspace_id: Callable[[], WorkspaceId],
        generate_user_revision_id: Callable[[], UserLifecycleRevisionId],
        generate_workspace_revision_id: Callable[[], WorkspaceLifecycleRevisionId],
    ) -> None:
        self._engine = engine
        self._generate_user_id = generate_user_id
        self._generate_workspace_id = generate_workspace_id
        self._generate_user_revision_id = generate_user_revision_id
        self._generate_workspace_revision_id = generate_workspace_revision_id

    def __repr__(self) -> str:
        return "DatabaseInitialIdentityAuthorityBootstrap()"

    def bootstrap(self) -> BootstrappedIdentityAuthority | None:
        try:
            with self._engine.begin() as transaction:
                return self._bootstrap(transaction)
        except IdentityAuthorityBootstrapUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise IdentityAuthorityBootstrapUnavailable

    def _bootstrap(
        self, transaction: Connection
    ) -> BootstrappedIdentityAuthority | None:
        if transaction.dialect.name == "postgresql":
            transaction.execute(_LOCK_FOUNDATION)
        elif transaction.dialect.name != "sqlite":
            raise IdentityAuthorityBootstrapUnavailable

        if transaction.scalar(_HAS_INVENTORY):
            return None

        generated_user = self._generate_user_id()
        generated_workspace = self._generate_workspace_id()
        generated_user_revision = self._generate_user_revision_id()
        generated_workspace_revision = self._generate_workspace_revision_id()
        user = _encode(generated_user)
        workspace = _encode(generated_workspace)
        if type(generated_user_revision) is not UserLifecycleRevisionId:
            raise IdentityAuthorityBootstrapUnavailable
        if type(generated_workspace_revision) is not WorkspaceLifecycleRevisionId:
            raise IdentityAuthorityBootstrapUnavailable
        user_revision = _encode(generated_user_revision.value)
        workspace_revision = _encode(generated_workspace_revision.value)

        transaction.execute(_INSERT_USER, {"user": user})
        transaction.execute(_INSERT_WORKSPACE, {"workspace": workspace})
        transaction.execute(
            _INSERT_AUTHORITY, {"user": user, "workspace": workspace}
        )
        transaction.execute(_INSERT_USER_LIFECYCLE_AUTHORITY, {"user": user})
        transaction.execute(_INSERT_WORKSPACE_LIFECYCLE_AUTHORITY, {"user": user})
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
        return BootstrappedIdentityAuthority(
            user_id=UserId(str(generated_user)),
            workspace_id=WorkspaceId(str(generated_workspace)),
        )
