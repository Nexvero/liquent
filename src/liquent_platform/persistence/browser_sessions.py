"""Persistent lookup, creation, rotation, and revocation of browser sessions."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import (
    BrowserSessionRecord,
    IssuedBrowserSession,
    ResolvedBrowserSession,
    SessionId,
    SessionPrincipal,
)
from liquent_platform.persistence.identity_errors import BrowserSessionStoreUnavailable

_SELECT = text(
    "SELECT sessions.* FROM browser_sessions AS sessions"
    " JOIN identity_users AS users ON users.user_id=sessions.user_id"
    " WHERE sessions.session_id=:session AND users.status='active'"
)
_LOCK = text("SELECT * FROM browser_sessions WHERE session_id=:session FOR UPDATE")
_ACTIVE_USER = text(
    "SELECT 1 FROM identity_users WHERE user_id=:user AND status='active'"
)
_ACTIVE_USER_POSTGRES = text(str(_ACTIVE_USER) + " FOR UPDATE")
_INSERT = text(
    "INSERT INTO browser_sessions"
    " (session_id,user_id,csrf_token,expires_at,revoked_at)"
    " VALUES (:session,:user,:csrf,:expires,NULL)"
    " ON CONFLICT (session_id) DO NOTHING"
)
_REVOKE = text(
    "UPDATE browser_sessions SET revoked_at=:now"
    " WHERE session_id=:session AND revoked_at IS NULL"
)


def _encode(value: object) -> bytes:
    if type(value) is not str or not value:
        raise BrowserSessionStoreUnavailable
    return value.encode("utf-8")


def _decode(value: object) -> str:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise BrowserSessionStoreUnavailable
    try:
        result = bytes(value).decode("utf-8")
    except UnicodeDecodeError:
        raise BrowserSessionStoreUnavailable from None
    if not result:
        raise BrowserSessionStoreUnavailable
    return result


def _aware(value: object) -> datetime:
    if type(value) is str:
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            raise BrowserSessionStoreUnavailable from None
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise BrowserSessionStoreUnavailable
    return value


class DatabaseBrowserSessions:
    """Database-backed implementation of all stable browser-session ports."""

    __slots__ = ("_engine", "_now")

    def __init__(self, engine: Engine, *, now: Callable[[], datetime]) -> None:
        self._engine, self._now = engine, now

    def __repr__(self) -> str:
        return "DatabaseBrowserSessions()"

    def get_session(self, session_id: SessionId) -> ResolvedBrowserSession | None:
        try:
            with self._engine.connect() as connection:
                row = connection.execute(
                    _SELECT, {"session": _encode(session_id)}
                ).first()
            if row is None or row.revoked_at is not None:
                return None
            if _aware(self._now()) >= _aware(row.expires_at):
                return None
            return ResolvedBrowserSession(
                principal=SessionPrincipal(UserId(_decode(row.user_id))),
                expected_csrf_token=_decode(row.csrf_token),
            )
        except BrowserSessionStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise BrowserSessionStoreUnavailable

    def add_session(self, session_id: SessionId, record: BrowserSessionRecord) -> bool:
        try:
            with self._engine.begin() as connection:
                user = _encode(record.session.principal.user_id)
                active_user = (
                    _ACTIVE_USER_POSTGRES
                    if connection.dialect.name == "postgresql"
                    else _ACTIVE_USER
                )
                if connection.execute(active_user, {"user": user}).first() is None:
                    return False
                inserted = connection.execute(
                    _INSERT,
                    {
                        "session": _encode(session_id),
                        "user": user,
                        "csrf": _encode(record.session.expected_csrf_token),
                        "expires": _aware(record.expires_at),
                    },
                )
                return inserted.rowcount == 1
        except BrowserSessionStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise BrowserSessionStoreUnavailable

    def rotate_session(
        self, current_id: SessionId, replacement: IssuedBrowserSession
    ) -> bool:
        try:
            with self._engine.begin() as connection:
                query = _LOCK if connection.dialect.name == "postgresql" else _SELECT
                current = connection.execute(
                    query, {"session": _encode(current_id)}
                ).first()
                if current is None or current.revoked_at is not None:
                    return False
                active_user = (
                    _ACTIVE_USER_POSTGRES
                    if connection.dialect.name == "postgresql"
                    else _ACTIVE_USER
                )
                if connection.execute(
                    active_user, {"user": current.user_id}
                ).first() is None:
                    return False
                now = _aware(self._now())
                if now >= _aware(current.expires_at) or now >= _aware(
                    replacement.expires_at
                ):
                    return False
                inserted = connection.execute(
                    _INSERT,
                    {
                        "session": _encode(replacement.session_id),
                        "user": current.user_id,
                        "csrf": _encode(replacement.csrf_token),
                        "expires": _aware(replacement.expires_at),
                    },
                )
                if inserted.rowcount != 1:
                    return False
                if connection.execute(
                    _REVOKE, {"now": now, "session": _encode(current_id)}
                ).rowcount != 1:
                    raise BrowserSessionStoreUnavailable
                return True
        except BrowserSessionStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise BrowserSessionStoreUnavailable

    def revoke_session(self, session_id: SessionId) -> None:
        try:
            with self._engine.begin() as connection:
                query = _LOCK if connection.dialect.name == "postgresql" else _SELECT
                row = connection.execute(
                    query, {"session": _encode(session_id)}
                ).first()
                if row is None or row.revoked_at is not None:
                    return
                now = _aware(self._now())
                if now >= _aware(row.expires_at):
                    return
                connection.execute(
                    _REVOKE, {"now": now, "session": _encode(session_id)}
                )
            return
        except BrowserSessionStoreUnavailable as error:
            if error.__cause__ is None and error.__context__ is None:
                raise
        except Exception:
            pass
        raise BrowserSessionStoreUnavailable
