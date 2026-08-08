"""Turn one verified OIDC callback into exactly one fresh browser session."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from liquent_platform.application.issue_session import issue_browser_session
from liquent_platform.application.oidc_login_errors import (
    OidcLoginCompletionUnavailable,
)
from liquent_platform.application.verify_oidc_callback import VerifiedOidcCallback
from liquent_platform.identity.ports import (
    BrowserSessionCreationStore,
    BrowserSessionMaterialGenerator,
    ExternalIdentityAdmissionStore,
    ExternalIdentityLookup,
)
from liquent_platform.identity.session import IssuedBrowserSession, SessionPrincipal


@dataclass(frozen=True, slots=True)
class CompletedOidcLogin:
    """Exactly what a later transport boundary needs, and nothing else.

    Both fields are ``repr``-free, so neither session material nor a navigation
    target reaches a log through an object representation. The ``return_path``
    is carried verbatim and stays **unvalidated**: handing it on is a lossless
    handover to a separate destination boundary, not a redirect clearance.
    """

    session: IssuedBrowserSession = field(repr=False)
    return_path: str | None = field(repr=False)


def complete_oidc_login(
    identity_lookup: ExternalIdentityLookup,
    admission_store: ExternalIdentityAdmissionStore,
    session_store: BrowserSessionCreationStore,
    generator: BrowserSessionMaterialGenerator,
    verified: VerifiedOidcCallback,
    *,
    clock: Callable[[], datetime],
    lifetime: timedelta,
) -> CompletedOidcLogin | None:
    """Resolve one internal user and issue one fresh session, or reject.

    Runs after the callback was verified and its transaction claimed (LQ-163),
    so it sees no authorization code, token, state, cookie, or ambient session
    id, re-checks nothing, and never creates a user. ``None`` is the single
    business rejection and distinguishes nothing; OidcLoginCompletionUnavailable
    reports technical unavailability without any internal detail.

    The clock is injected and read **exactly once**, only after a user is
    settled, so a rejection produces neither a reading nor session material.
    """

    try:
        return _complete(
            identity_lookup,
            admission_store,
            session_store,
            generator,
            verified,
            clock=clock,
            lifetime=lifetime,
        )
    except OidcLoginCompletionUnavailable as error:
        # Only an error whose own chain is clean keeps its identity; one still
        # carrying an inner error is replaced below.
        if error.__cause__ is None and error.__context__ is None:
            raise
    except Exception:
        # Lookup, admission store, clock, generator, session creation, and a
        # refused session write alike. BaseException is deliberately not caught.
        pass

    # Raised outside the handler, so it carries neither a cause nor a context.
    raise OidcLoginCompletionUnavailable


def _complete(
    identity_lookup: ExternalIdentityLookup,
    admission_store: ExternalIdentityAdmissionStore,
    session_store: BrowserSessionCreationStore,
    generator: BrowserSessionMaterialGenerator,
    verified: VerifiedOidcCallback,
    *,
    clock: Callable[[], datetime],
    lifetime: timedelta,
) -> CompletedOidcLogin | None:
    # Checked before the lookup, so an unusable configuration can never consume
    # an admission on its way to failing.
    if lifetime <= timedelta(0):
        raise OidcLoginCompletionUnavailable

    user_id = identity_lookup.get_user_id(verified.identity)
    if user_id is None:
        if verified.admission_id is None:
            # Unbound and unadmitted: a neutral rejection, and nothing is read
            # or generated on the way out.
            return None
        # The only atomic write. Its result decides alone: no second lookup, no
        # fallback, and no check-then-act.
        user_id = admission_store.consume_admission_and_bind(
            verified.admission_id, verified.identity
        )
        if user_id is None:
            return None
    # An already bound identity resolves read-only, so a present admission stays
    # unread and unconsumed: it is a capability for a first binding only.

    issued = issue_browser_session(
        session_store,
        generator,
        SessionPrincipal(user_id),
        now=_read_clock(clock),
        lifetime=lifetime,
    )
    return CompletedOidcLogin(issued, verified.return_path)


def _read_clock(clock: Callable[[], datetime]) -> datetime:
    moment = clock()
    # A wrongly typed or naive instant cannot bound a session's validity.
    if not isinstance(moment, datetime):
        raise OidcLoginCompletionUnavailable
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise OidcLoginCompletionUnavailable
    return moment
