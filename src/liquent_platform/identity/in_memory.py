"""Local identity adapters with no persistence or shared-environment role."""

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import datetime

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
