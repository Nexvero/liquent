"""Ports required by the identity and authorization capability."""

from typing import Protocol

from liquent_platform.identity.access import UserId, WorkspaceMembership
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    IssuedBrowserSession,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)


class WorkspaceMembershipLookup(Protocol):
    """Find the membership for one user and one workspace."""

    def get_membership(
        self, user_id: UserId, workspace_id: WorkspaceId
    ) -> WorkspaceMembership | None: ...


class BrowserSessionLookup(Protocol):
    """Resolve one opaque session identifier without exposing storage details."""

    def get_session(self, session_id: SessionId) -> ResolvedBrowserSession | None: ...


class ExternalIdentityLookup(Protocol):
    """Resolve one verified external identity to an internal user, read-only."""

    def get_user_id(self, identity: ExternalIdentity) -> UserId | None: ...


class BrowserSessionLifecycle(Protocol):
    """Create, rotate, and revoke server-side browser sessions."""

    def create_session(self, principal: SessionPrincipal) -> IssuedBrowserSession: ...

    def rotate_session(
        self, session_id: SessionId
    ) -> IssuedBrowserSession | None: ...

    def revoke_session(self, session_id: SessionId) -> None: ...


class BrowserSessionCreationStore(Protocol):
    """Atomically add one new session without replacing an existing record."""

    def add_session(
        self,
        session_id: SessionId,
        record: BrowserSessionRecord,
    ) -> bool: ...


class BrowserSessionRotationStore(Protocol):
    """Atomically revoke a valid session and add a replacement bound to its principal.

    The store reads the current record, reuses its unchanged principal for the
    replacement, revokes the old record, and adds the new one in one step. The
    caller never supplies a principal, so a replacement cannot bind a foreign one.
    """

    def rotate_session(
        self,
        current_id: SessionId,
        replacement: IssuedBrowserSession,
    ) -> bool: ...


class BrowserSessionRevocationStore(Protocol):
    """Idempotently revoke one browser session without revealing its state.

    Unknown, already revoked, or expired sessions are neutral no-ops. The
    return value never signals whether a session existed or was valid.
    """

    def revoke_session(self, session_id: SessionId) -> None: ...


class BrowserSessionMaterialGenerator(Protocol):
    """Generate independent opaque material for one new browser session."""

    def new_session_id(self) -> SessionId: ...

    def new_csrf_token(self) -> str: ...
