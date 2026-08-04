"""Neutral application errors for OIDC login start conflicts."""


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
