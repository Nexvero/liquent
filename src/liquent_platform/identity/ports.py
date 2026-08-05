"""Ports required by the identity and authorization capability."""

from typing import Protocol

from liquent_platform.identity.access import UserId, WorkspaceMembership
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
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

    An existing but expired transaction returns None outwardly and its
    secret-bearing pending state is atomically removed or permanently treated as
    consumed in the same step: expected_nonce and code_verifier must not become
    available again through that state. A persistent implementation may instead
    leave a secret-free consumption proof or tombstone behind. No secrets are
    kept in an expired pending state.

    This port verifies no OIDC token and no current issuer-trust configuration.
    The successful result briefly carries the secrets needed for exactly this
    callback; their further use belongs to a later use case. A persistent
    implementation may keep a separate consumption proof or tombstone.
    """

    def claim_transaction(
        self,
        state: OidcLoginState,
    ) -> PendingOidcLoginTransaction | None: ...


class OidcLoginTransactionCreationStore(Protocol):
    """Atomically store one new pending login transaction without reusing a state.

    Success returns True and keeps exactly the given immutable record under the
    exact opaque state; neither is normalized or altered. An existing pending
    record is never overwritten, so a state that is already pending returns a
    neutral False. A state that was previously claimed, consumed, or dropped on
    expiry and is known through a consumption proof or tombstone must not be
    reused and returns the same neutral False: an old callback can therefore
    never meet a new login transaction by re-occupying its state. False does not
    distinguish a pending collision from an already used state. A persistent
    store must secure that non-reuse atomically; a later local adapter may keep
    an internal, secret-free reserved/used state set for it.

    The caller supplies no ``now``, and this port decides nothing about issuer
    trust, OIDC tokens, admission, or authorization. Ensuring the record has not
    already expired at creation time belongs to the later login-start use case.
    The store performs no automatic retry and generates no material, and no
    secrets are logged or carried in a failure result.
    """

    def add_transaction(
        self,
        state: OidcLoginState,
        transaction: PendingOidcLoginTransaction,
    ) -> bool: ...


class ActiveOidcClientConfigurationLookup(Protocol):
    """Read the one currently active OIDC client configuration, read-only.

    The method takes no argument beyond ``self``. Liquent supports exactly one
    active configuration at this boundary, so no issuer, provider, client id,
    tenant, workspace, user, host, header, query value, cookie, admission
    handle, return path, or other selector can be passed. A later HTTP boundary
    therefore cannot hand a browser-chosen provider to this port at all: the
    protection is structural, not a runtime check.

    A returned configuration is exactly the stored immutable object — not a
    copy with altered values, nothing normalized, nothing added, no secret
    attached. Holding it freezes no trust status: every login start reads the
    current configuration again, and the callback must still re-check the
    current issuer trust separately.

    ``None`` means only that no active OIDC client configuration is available
    for login right now. It never distinguishes "never configured" from
    "deactivated" or "approval revoked", and it reveals no previously
    configured issuer or client; a later transport boundary must keep that
    neutrality. The port returns no list, no deactivated configuration, no
    alternative or default fallback, and no detail reason.

    A genuine read, configuration, or infrastructure failure must not be
    silently turned into ``None``. This port defines no error type and no error
    handling of its own; a later application or transport boundary handles
    failures neutrally without faking an empty state.

    The port only reads. It activates and deactivates nothing, creates,
    updates, deletes, and rotates nothing, runs no discovery, loads no signing
    key set, performs no network call, requires no caching, and decides no
    workspace permission. Supporting several trusted issuers later needs its
    own contract and must not silently change the meaning of this method.
    """

    def get_active_configuration(
        self,
    ) -> TrustedOidcClientConfiguration | None: ...


class OidcAuthorizationCodeVerifier(Protocol):
    """Redeem one authorization code and return only a verified identity.

    This is level three of the LQ-155 callback: it is reached **only after** the
    browser binding matched and the login transaction was claimed atomically
    exactly once. The single argument carries the authorization code and the
    four verification-relevant values of that already claimed transaction.

    **Success.** An ExternalIdentity is returned only when an implementation has
    completed all of the following: read the active configuration exactly once;
    found one present; matched its issuer byte for byte against the stored
    expected_issuer; redeemed the code exactly once at the configured token
    endpoint using the stored code_verifier and the stored redirect_uri
    unchanged; verified the ID token's signature under an explicitly allowed
    algorithm; taken the key solely from the configured trusted JWKS set;
    verified iss, aud, azp where several audiences are present, exp, nbf, iat,
    and nonce in full; and found a non-empty sub. The result is exactly
    ExternalIdentity(issuer, subject) and carries no token, claim, or other
    value. A successful token endpoint response is never a reason to skip one of
    these checks.

    **Business rejection.** ``None`` is the only business rejection and
    distinguishes nothing: no active configuration, an expected issuer that is
    no longer active, a refused or invalid code, a missing or invalid token, a
    signature, algorithm, key, or claim failure, an issuer, audience, azp, time,
    or nonce failure, and a missing or empty subject all look identical. It
    carries no cause and no existence information, so a caller cannot learn
    whether a configuration, identity, or subject exists.

    **Technical unavailability.** OidcVerificationUnavailable is raised instead
    when the verification could not be carried out at all — an unreadable
    configuration store, a network failure, an unreachable token endpoint or
    JWKS source, key verification that cannot be performed safely, or an
    internal adapter or library fault. An implementation must translate its
    internal failures into that neutral error rather than let one propagate that
    could carry a code, token, nonce, verifier, issuer, provider text, or
    configuration detail.

    **Consumption.** This port claims no login transaction, sees no state, and
    performs no store rollback; it cannot tell whether a transaction ever
    existed. It is called only after the atomic claim, so the transaction is
    already consumed in every outcome and stays consumed. Neither ``None`` nor
    OidcVerificationUnavailable is retryable for the same transaction — a new
    attempt needs a new login start, because a retry would be a replay path.

    The port selects no provider, accepts no issuer, tenant, client, host,
    header, cookie, or request value, reads no clock from its caller, resolves
    no identity to a UserId, consumes no admission, and creates no session. A
    returned identity means only that this external identity was fully verified
    for exactly this login transaction.
    """

    def verify_authorization_code(
        self,
        verification: OidcAuthorizationCodeVerification,
    ) -> ExternalIdentity | None: ...


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
