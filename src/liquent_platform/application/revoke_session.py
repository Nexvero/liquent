"""Revoke one browser session through a neutral, idempotent store port."""

from liquent_platform.identity.ports import BrowserSessionRevocationStore
from liquent_platform.identity.session import SessionId


def revoke_browser_session(
    store: BrowserSessionRevocationStore,
    session_id: SessionId,
) -> None:
    """Delegate a single idempotent revocation without storage or time logic.

    Returns nothing, so the outcome never reveals whether the session existed
    or was still valid.
    """

    store.revoke_session(session_id)
