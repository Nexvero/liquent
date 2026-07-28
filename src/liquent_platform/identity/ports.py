"""Ports required by the identity and authorization capability."""

from typing import Protocol

from liquent_platform.identity.access import UserId, WorkspaceMembership
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
