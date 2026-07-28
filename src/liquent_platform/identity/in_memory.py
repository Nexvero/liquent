"""Local identity adapters with no persistence or shared-environment role."""

from collections.abc import Callable, Mapping
from datetime import datetime

from liquent_platform.identity.session import (
    BrowserSessionRecord,
    ResolvedBrowserSession,
    SessionId,
    resolve_valid_session,
)


class InMemoryBrowserSessions:
    """Browser-session lookup and creation store for tests and local execution."""

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
