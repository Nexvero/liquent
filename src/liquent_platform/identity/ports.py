"""Ports required by the identity and authorization capability."""

from typing import Protocol

from liquent_platform.identity.access import UserId, WorkspaceMembership
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
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


class ExternalIdentityAdmissionStore(Protocol):
    """Atomically consume one admission and create its first identity binding.

    The target user is taken solely from the internally stored admission; the
    caller never supplies a UserId, so a login/callback caller cannot bind an
    external identity to a freely chosen or foreign user. Admission validity,
    expiry, single-use consumption, and the first binding happen atomically. On
    success the internally determined UserId is returned; an exact repeat of the
    same completed operation is idempotent and returns the same UserId. An
    unknown, expired, or otherwise consumed admission, an identity collision, or
    a binding to a different user all fail neutrally to None, indistinguishably.
    """

    def consume_admission_and_bind(
        self,
        admission_id: IdentityAdmissionId,
        identity: ExternalIdentity,
    ) -> UserId | None: ...


class OidcLoginTransactionClaimStore(Protocol):
    """Atomically claim one pending login transaction exactly once.

    Before succeeding the store checks that the transaction exists, is still
    pending, and has not expired. It reads its own clock: the caller supplies
    neither ``now`` nor any expiry decision, and beyond the state it supplies no
    issuer, nonce, verifier, admission handle, or other transaction material.
    Success consumes or removes the pending state fail-closed and hands the
    PendingOidcLoginTransaction to the callback process exactly once; a second
    claim of the same state returns None. Unknown, expired, and already claimed
    states are indistinguishable None, revealing nothing about an admission,
    issuer, user, or transaction state.

    This port verifies no OIDC token and no current issuer-trust configuration.
    The successful result briefly carries the secrets needed for exactly this
    callback; their further use belongs to a later use case. A persistent
    implementation may keep a separate consumption proof or tombstone.
    """

    def claim_transaction(
        self,
        state: OidcLoginState,
    ) -> PendingOidcLoginTransaction | None: ...


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
