"""Secure HTTP cookie handling for opaque browser-session identifiers."""

from datetime import datetime

from fastapi import Response

from liquent_platform.identity.session import IssuedBrowserSession


SESSION_COOKIE_NAME = "liquent_session"


def set_session_cookie(
    response: Response,
    issued: IssuedBrowserSession,
    *,
    now: datetime,
) -> None:
    """Attach a host-only session cookie bounded by server-side expiry."""

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    remaining_seconds = int((issued.expires_at - now).total_seconds())
    if remaining_seconds <= 0:
        raise ValueError("session cookie expiry must be in the future")

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=str(issued.session_id),
        max_age=remaining_seconds,
        expires=issued.expires_at,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"


def clear_session_cookie(response: Response) -> None:
    """Expire the session cookie with the same transport attributes."""

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
