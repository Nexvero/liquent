"""Host-only browser-binding cookie for one OIDC login transaction."""

from datetime import UTC, datetime, timedelta

from fastapi import Response


OIDC_STATE_COOKIE_NAME = "__Host-liquent_oidc_state"


def set_oidc_state_cookie(
    response: Response,
    state_value: str,
    *,
    now: datetime,
    lifetime: timedelta,
) -> None:
    """Bind one freshly started login transaction to exactly this browser.

    The ``__Host-`` prefix is the point of this helper and is deliberately
    different from the prefix-less ``liquent_session`` cookie (LQ-117/LQ-118),
    which stays untouched. The prefix forces ``Secure``, requires ``Path=/``,
    and forbids ``Domain``, so a compromised sibling subdomain cannot overwrite
    this cookie and defeat the browser binding. ``SameSite=Lax`` is sufficient
    because the callback arrives as a top-level GET navigation; ``None`` is
    forbidden.

    The lifetime bounds the cookie: ``Max-Age`` is the truncated whole-second
    lifetime and therefore never exceeds the server-side transaction lifetime,
    and ``Expires`` is the same ``now`` the transaction was stored with plus
    that lifetime. ``expires`` is normalized to UTC because the header format
    requires it — an aware non-UTC clock would otherwise raise here, after the
    transaction was already stored atomically, and leave an orphan record for no
    reason.

    The value is exactly the state handed over by the use case. It is never
    recovered by parsing the authorization URL, which would be a second and
    weaker source for a security-critical value. The cookie is ``HttpOnly``, is
    no authentication proof, and grants no permission; it only correlates one
    later callback with the browser that started the login.

    There is exactly one slot for this name — same ``Path=/``, no ``Domain`` —
    so a new successful start overwrites the previous binding: last-start-wins.
    """

    if lifetime <= timedelta(0):
        raise ValueError("login transaction lifetime must be positive")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if not state_value:
        raise ValueError("login state must not be empty")

    response.set_cookie(
        key=OIDC_STATE_COOKIE_NAME,
        value=state_value,
        max_age=int(lifetime.total_seconds()),
        expires=(now + lifetime).astimezone(UTC),
        path="/",
        # No domain: the __Host- prefix forbids it and host-only is the point.
        secure=True,
        httponly=True,
        samesite="lax",
    )


def clear_oidc_state_cookie(response: Response) -> None:
    """Expire the binding cookie with the same transport attributes.

    Deletion must address the exact same single slot the setter wrote — same
    name, ``Path=/``, and no ``Domain`` — because a browser matches a deletion
    by those attributes. A deletion that differed in any of them would leave the
    original cookie in place and silently keep a reusable binding proof.

    This is a pure response mutation. It reads no request cookie, decides
    nothing about whether a cookie was present, and therefore is no
    existence oracle: calling it looks identical whether or not the browser
    sent one. Whether and when it is called belongs to a later callback slice.
    Per LQ-158 it is used only **after** a successful state/cookie match; a
    missing cookie and a mismatch deliberately do **not** reach it, because
    writing this slot could otherwise clear a newer, still valid binding.

    The existing ``liquent_session`` cookie is untouched.
    """

    response.delete_cookie(
        key=OIDC_STATE_COOKIE_NAME,
        path="/",
        # No domain, exactly as when set: the __Host- prefix forbids it.
        secure=True,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
