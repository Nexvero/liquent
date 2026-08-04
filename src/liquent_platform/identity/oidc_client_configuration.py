"""One already trusted OIDC issuer and client configuration, provider-neutral."""

from dataclasses import dataclass
from urllib.parse import urlsplit


def _require_https_url(value: str, name: str, *, allow_query: bool) -> None:
    """Validate one absolute https URL without ever rewriting it.

    The value is only inspected: nothing is normalized, canonicalized, or
    returned, so the caller keeps the exact configured string. No network call,
    no DNS lookup, and no discovery happens here. Messages name the field but
    never echo the value, so a rejected configuration cannot leak through an
    error.
    """

    if not value:
        raise ValueError(f"{name} must not be empty")
    parsed = urlsplit(value)
    if parsed.scheme != "https":
        raise ValueError(f"{name} must be an absolute https url")
    if not parsed.hostname:
        raise ValueError(f"{name} must have a host")
    # Checked against None rather than truthiness so an empty userinfo such as
    # "https://@host/" is rejected too.
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{name} must not contain userinfo")
    if parsed.query and not allow_query:
        raise ValueError(f"{name} must not contain a query")
    if parsed.fragment:
        raise ValueError(f"{name} must not contain a fragment")


@dataclass(frozen=True, slots=True)
class TrustedOidcClientConfiguration:
    """One issuer and client already selected from trusted server configuration.

    Holding this object is **not** proof that the issuer is still enabled. It
    carries no activation or trust flag and freezes no trust decision: choosing
    a currently trusted issuer stays the job of a later registry or application
    boundary, and the callback must re-check the current issuer trust. A stored
    configuration must therefore never bypass a permission that was revoked in
    the meantime.

    No browser value may construct this object or override a field. Every value
    comes from active server-side configuration, and the later login start and
    authorization request must use exactly these strings.

    All five values are kept verbatim after validation: no trimming, no
    lowercasing, no slash removal, no URL canonicalization, and no scope
    sorting, deduplication, or completion. Two differently spelled issuers stay
    two different configurations, so the calling trust boundary must already
    supply the canonical value. The issuer is never derived from the
    authorization endpoint, and the redirect URI is never derived from any
    other field, header, or request value.

    The object carries nothing else — no client secret, tokens, claims,
    subject, user, admission, workspace, role, session data, state, nonce, code
    verifier, code challenge, return path, discovery or JWKS material, and no
    provider name or branding.
    """

    issuer: str
    authorization_endpoint: str
    client_id: str
    redirect_uri: str
    scopes: tuple[str, ...]

    def __post_init__(self) -> None:
        # The issuer and the authorization endpoint must not carry a query: a
        # configured endpoint is rejected rather than merged (LQ-145), which
        # rules out collision with the mandatory parameters by construction.
        _require_https_url(self.issuer, "issuer", allow_query=False)
        _require_https_url(
            self.authorization_endpoint,
            "authorization_endpoint",
            allow_query=False,
        )
        if not self.client_id:
            raise ValueError("client_id must not be empty")
        # A redirect URI may carry a fixed configured query, because OIDC
        # redirect URIs are registered values compared exactly.
        _require_https_url(self.redirect_uri, "redirect_uri", allow_query=True)
        self._validate_scopes()

    def _validate_scopes(self) -> None:
        if not isinstance(self.scopes, tuple):
            raise ValueError("scopes must be a tuple")
        if not self.scopes:
            raise ValueError("scopes must not be empty")
        seen: set[str] = set()
        for scope in self.scopes:
            if not isinstance(scope, str):
                raise ValueError("each scope must be a string")
            if not scope:
                raise ValueError("scope must not be empty")
            # Scopes are serialized as space-delimited tokens later, so an
            # embedded space, tab, or newline is rejected instead of normalized.
            if any(character.isspace() for character in scope):
                raise ValueError("scope must not contain whitespace")
            if scope in seen:
                raise ValueError("scopes must not repeat")
            seen.add(scope)
        if "openid" not in seen:
            raise ValueError("scopes must contain openid")
