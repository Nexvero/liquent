"""Neutral application errors raised while starting or completing an OIDC login."""


class OidcLoginUnavailable(Exception):
    """Report that no active OIDC client configuration is available for login.

    Kept apart from OidcLoginStartConflict on purpose: a missing active
    configuration and a rejected state are different situations, and merging
    them would make two unrelated causes indistinguishable to the caller.

    The error carries the neutrality of the lookup forward. It never says
    whether a configuration was never present, was deactivated, or had its
    approval revoked, and it holds no issuer, endpoint, client id, redirect
    uri, or any other configuration or existence detail.
    """

    code = "oidc_login_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcLoginStartConflict(Exception):
    """Report a rejected atomic login-transaction creation without details.

    The store returned a neutral False, which does not distinguish a still
    pending state from an already claimed, expired, or otherwise used one. This
    error carries that neutrality forward: it never holds a state, nonce, code
    verifier, issuer, redirect URI, admission id, or any other internal value,
    so it cannot reveal whether a login transaction already exists.
    """

    code = "oidc_login_start_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class OidcLoginCompletionUnavailable(Exception):
    """Report that a verified callback could not be completed into a session.

    Kept apart from the neutral ``None`` of a business rejection and from the
    verification boundary's own error: an unreadable lookup, an admission store
    fault, an unusable clock, a generator fault, and a refused session write are
    all technical, while an unbound identity or a refused admission are not.

    It holds no identity, user, admission id, session id, csrf token, return
    path, or internal cause, so it reveals nothing about what exists.
    """

    code = "oidc_login_completion_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)
