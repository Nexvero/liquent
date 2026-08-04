"""Local identity adapters with no persistence or shared-environment role."""

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import datetime

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    IdentityAdmissionRecord,
)
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    IssuedBrowserSession,
    ResolvedBrowserSession,
    SessionId,
    resolve_valid_session,
)


class InMemoryBrowserSessions:
    """Browser-session lookup, creation, rotation, and revocation store for local execution."""

    def __init__(
        self,
        records: Mapping[SessionId, BrowserSessionRecord],
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._records = dict(records)
        self._now = now

    def get_session(self, session_id: SessionId) -> ResolvedBrowserSession | None:
        record = self._records.get(session_id)
        if record is None:
            return None
        return resolve_valid_session(record, now=self._now())

    def add_session(
        self,
        session_id: SessionId,
        record: BrowserSessionRecord,
    ) -> bool:
        """Add a new record without replacing an existing session identifier."""

        if session_id in self._records:
            return False
        self._records[session_id] = record
        return True

    def rotate_session(
        self,
        current_id: SessionId,
        replacement: IssuedBrowserSession,
    ) -> bool:
        """Atomically revoke a valid session and add its principal-bound replacement.

        Returns True only when the current session is present and valid, the
        replacement identifier is free and different, and the replacement is not
        already expired. Any other case leaves all records unchanged and returns
        a neutral False. The injected clock is read at most once and only after
        the source exists and a time check is required.
        """

        current = self._records.get(current_id)
        if current is None:
            return False
        if replacement.session_id == current_id:
            return False
        if replacement.session_id in self._records:
            return False

        now = self._now()
        if resolve_valid_session(current, now=now) is None:
            return False
        if now >= replacement.expires_at:
            return False

        new_record = BrowserSessionRecord(
            ResolvedBrowserSession(
                current.session.principal,
                replacement.csrf_token,
            ),
            replacement.expires_at,
        )
        snapshot = dict(self._records)
        snapshot[current_id] = replace(current, revoked_at=now)
        snapshot[replacement.session_id] = new_record
        self._records = snapshot
        return True

    def revoke_session(self, session_id: SessionId) -> None:
        """Idempotently revoke one session without revealing its state.

        Unknown and already revoked sessions are neutral no-ops that do not read
        the clock. An expired session is left unchanged. An active session is
        revoked with a single clock read; a fully built records snapshot is
        swapped in one step so all other records stay unchanged. Returns nothing.
        """

        record = self._records.get(session_id)
        if record is None:
            return
        if record.revoked_at is not None:
            return

        now = self._now()
        if resolve_valid_session(record, now=now) is None:
            return

        snapshot = dict(self._records)
        snapshot[session_id] = replace(record, revoked_at=now)
        self._records = snapshot


class InMemoryExternalIdentities:
    """External-identity lookup and admission store for tests and local execution."""

    def __init__(
        self,
        admissions: Mapping[IdentityAdmissionId, IdentityAdmissionRecord],
        bindings: Mapping[ExternalIdentity, UserId],
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._admissions = dict(admissions)
        self._bindings = dict(bindings)
        self._now = now

    def get_user_id(self, identity: ExternalIdentity) -> UserId | None:
        """Resolve one exact external identity to its bound user, read-only."""

        return self._bindings.get(identity)

    def consume_admission_and_bind(
        self,
        admission_id: IdentityAdmissionId,
        identity: ExternalIdentity,
    ) -> UserId | None:
        """Atomically consume one admission and create its first identity binding.

        The target user comes solely from the admission record. Structural
        neutral cases and an exact idempotent repeat are resolved before the
        clock is read; the clock is read at most once and only for a still
        active, unconsumed admission. Any failure returns a neutral None and
        leaves admission and binding state unchanged.
        """

        record = self._admissions.get(admission_id)
        if record is None:
            return None  # unknown admission; no clock read

        if record.consumed_at is not None:
            # Exact idempotent repeat: same identity and same existing binding.
            if (
                record.bound_identity == identity
                and self._bindings.get(identity) == record.target_user_id
            ):
                return record.target_user_id
            return None  # any other use of a consumed admission; no clock read

        # Unconsumed admission: structural neutral cases, still without the clock.
        if identity in self._bindings:
            return None  # identity already bound (possibly to another user)
        target_user_id = record.target_user_id
        if target_user_id in self._bindings.values():
            return None  # target already bound to another identity; no linking

        now = self._now()  # single clock read, only for an active unconsumed admission
        if now >= record.expires_at:
            return None  # expired (also exactly at expiry); state unchanged

        # Success: fully prepare both new snapshots, then adopt them together.
        new_admissions = dict(self._admissions)
        new_admissions[admission_id] = replace(
            record, consumed_at=now, bound_identity=identity
        )
        new_bindings = dict(self._bindings)
        new_bindings[identity] = target_user_id
        self._admissions = new_admissions
        self._bindings = new_bindings
        return target_user_id


class InMemoryOidcLoginTransactions:
    """Pending OIDC login transaction creation and claim store for local execution.

    Every state used by this instance stays reserved for its lifetime: claiming
    a transaction drops only the pending record, so a state is never accepted
    again and an old callback can never meet a new transaction under it. The
    reserved set holds raw OidcLoginState objects, which remain sensitive
    handles; they are never returned or logged. Persistent hashing stays outside
    this adapter, and nothing outlives the process.
    """

    def __init__(
        self,
        transactions: Mapping[OidcLoginState, PendingOidcLoginTransaction],
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._transactions = dict(transactions)
        self._reserved_states = set(self._transactions)
        self._now = now

    def add_transaction(
        self,
        state: OidcLoginState,
        transaction: PendingOidcLoginTransaction,
    ) -> bool:
        """Atomically store one new pending transaction under an unused state.

        A state that is still pending or was already used in this instance is a
        neutral False that overwrites nothing and reads no clock. For a free
        state both snapshots are fully prepared before either attribute is
        replaced, and exactly the given immutable record is kept under the exact
        state; neither is normalized. Nothing is retried or generated here, and
        expiry is not decided at creation time: the later login-start use case
        must supply a record that has not expired.
        """

        if state in self._reserved_states:
            return False  # still pending or already used; no reuse, no clock read

        new_transactions = dict(self._transactions)
        new_transactions[state] = transaction
        new_reserved_states = set(self._reserved_states)
        new_reserved_states.add(state)
        self._transactions = new_transactions
        self._reserved_states = new_reserved_states
        return True

    def claim_transaction(
        self,
        state: OidcLoginState,
    ) -> PendingOidcLoginTransaction | None:
        """Atomically claim one pending login transaction exactly once.

        An unknown or already claimed state is a neutral None resolved without
        reading the clock and leaves all state unchanged; an unknown state is
        not reserved by a failed claim. For a present record the clock is read
        once and the pending state is dropped before any result is returned, so
        success and expiry share the same fail-closed removal and an expired
        record's secrets stay unreachable through the store. The state itself
        stays reserved in both cases. Unknown, expired, and already claimed are
        indistinguishable.
        """

        pending = self._transactions.get(state)
        if pending is None:
            return None  # unknown or already claimed; no clock read

        now = self._now()  # single clock read, only for a present pending record

        # Drop the secret-bearing state first: build the full snapshot without
        # it and adopt it before deciding success or expiry.
        snapshot = dict(self._transactions)
        del snapshot[state]
        self._transactions = snapshot

        if now >= pending.expires_at:
            return None  # expired (also exactly at expiry); secrets now gone
        return pending
