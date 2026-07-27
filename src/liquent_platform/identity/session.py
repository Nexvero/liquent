"""Verified session identity passed into application use cases."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import NewType

from liquent_platform.identity.access import UserId


SessionId = NewType("SessionId", str)


@dataclass(frozen=True, slots=True)
class SessionPrincipal:
    """A user identity already verified by an outer session boundary."""

    user_id: UserId


@dataclass(frozen=True, slots=True)
class ResolvedBrowserSession:
    """Security context produced only after an outer session check succeeds."""

    principal: SessionPrincipal
    expected_csrf_token: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self.expected_csrf_token:
            raise ValueError("expected csrf token must not be empty")


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class BrowserSessionRecord:
    """Server-side session state awaiting a validity decision."""

    session: ResolvedBrowserSession
    expires_at: datetime
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware(self.expires_at, "expires_at")
        if self.revoked_at is not None:
            _require_aware(self.revoked_at, "revoked_at")


def resolve_valid_session(
    record: BrowserSessionRecord,
    *,
    now: datetime,
) -> ResolvedBrowserSession | None:
    """Return the bound context only while the record remains valid."""

    _require_aware(now, "now")
    if record.revoked_at is not None or now >= record.expires_at:
        return None
    return record.session


@dataclass(frozen=True, slots=True)
class IssuedBrowserSession:
    """New opaque browser-session material returned by a lifecycle command."""

    session_id: SessionId = field(repr=False)
    csrf_token: str = field(repr=False)
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session id must not be empty")
        if not self.csrf_token:
            raise ValueError("csrf token must not be empty")
        _require_aware(self.expires_at, "expires_at")
