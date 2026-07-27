from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    ResolvedBrowserSession,
    SessionPrincipal,
    resolve_valid_session,
)


NOW = datetime(2026, 7, 27, 12, tzinfo=UTC)


def _session() -> ResolvedBrowserSession:
    return ResolvedBrowserSession(
        SessionPrincipal(UserId("user-1")),
        "private-csrf-proof",
    )


def test_active_record_resolves_before_expiry() -> None:
    session = _session()
    record = BrowserSessionRecord(session, NOW + timedelta(minutes=1))

    assert resolve_valid_session(record, now=NOW) is session


@pytest.mark.parametrize(
    "current_time",
    [NOW, NOW + timedelta(seconds=1)],
)
def test_record_is_invalid_at_and_after_expiry(current_time: datetime) -> None:
    record = BrowserSessionRecord(_session(), NOW)

    assert resolve_valid_session(record, now=current_time) is None


def test_revoked_record_never_resolves() -> None:
    record = BrowserSessionRecord(
        _session(),
        NOW + timedelta(hours=1),
        revoked_at=NOW,
    )

    assert resolve_valid_session(record, now=NOW - timedelta(minutes=1)) is None


@pytest.mark.parametrize("field_name", ["expires_at", "revoked_at", "now"])
def test_session_times_must_be_timezone_aware(field_name: str) -> None:
    naive = datetime(2026, 7, 27, 12)

    with pytest.raises(ValueError, match=f"{field_name} must be timezone-aware"):
        if field_name == "expires_at":
            BrowserSessionRecord(_session(), naive)
        elif field_name == "revoked_at":
            BrowserSessionRecord(_session(), NOW, revoked_at=naive)
        else:
            resolve_valid_session(BrowserSessionRecord(_session(), NOW), now=naive)


def test_session_record_is_immutable() -> None:
    record = BrowserSessionRecord(_session(), NOW)

    with pytest.raises(FrozenInstanceError):
        record.expires_at = NOW + timedelta(hours=1)  # type: ignore[misc]
