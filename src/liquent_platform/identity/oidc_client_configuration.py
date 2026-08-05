"""One already trusted OIDC issuer and client configuration, provider-neutral."""

from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit


# The "small, explicit" skew bound LQ-155 requires. A larger window would widen
# the replay surface of every time-bound claim for no operational gain.
MAXIMUM_CLOCK_SKEW = timedelta(minutes=5)


def _require_https_url(value: str, name: str, *, allow_query: bool) -> None:
    """Validate one absolute https URL without ever rewriting it.

    The value is only inspected: nothing is normalized, canonicalized, or
    returned, so the caller keeps the exact configured string. No network call,
    no DNS lookup, and no discovery happens here. Messages name the field but
    never echo the value, so a rejected configuration cannot leak through an
    error.

    Two checks deliberately run against the raw string rather than the parse
    result, because the parser hides what they look for: it strips raw control
    characters, and it reports an empty query or fragment identically to an
    absent one. A present port is validated but neither added nor normalized.
    """

    if not value:
        raise ValueError(f"{name} must not be empty")
    # Checked on the raw value *before* parsing: urlsplit silently removes tab,
    # newline, and carriage return anywhere in the URL, even inside the host, so
    # a cleaned parse would otherwise validate while the unsafe original string
    # is what gets stored.
    if any(
        character.isspace() or ord(character) < 0x20 or ord(character) == 0x7F
        for character in value
    ):
        raise ValueError(f"{name} must not contain whitespace or control characters")
    parsed = urlsplit(value)
    if parsed.scheme != "https":
        raise ValueError(f"{name} must be an absolute https url")
    if not parsed.hostname:
        raise ValueError(f"{name} must have a host")
    # Checked against None rather than truthiness so an empty userinfo such as
    # "https://@host/" is rejected too.
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{name} must not contain userinfo")
    try:
        parsed.port  # noqa: B018 - the access itself validates the port syntax
    except ValueError:
        # The parser's own message quotes the offending port, so it is replaced
        # by a neutral one. No default port is added and none is normalized.
        raise ValueError(f"{name} must have a valid port") from None
    # Separators are detected on the raw value: for "https://host/a?" and
    # "https://host/a#" both parsed.query and parsed.fragment are empty strings,
    # so a truthiness check would let an empty separator through.
    if "?" in value and not allow_query:
        raise ValueError(f"{name} must not contain a query")
    if "#" in value:
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

    The object carries nothing else — no client secret, private key, tokens,
    claims, subject, user, admission, workspace, role, session data, state,
    nonce, code verifier, code challenge, return path, and no provider name or
    branding.

    The four verification values added by LQ-156 — ``token_endpoint``,
    ``jwks_uri``, ``allowed_signing_algorithms``, and ``clock_skew`` — come
    solely from trusted server configuration. They are never derived from
    browser input, a pending login transaction, token claims, or headers, and
    they freeze no trust status: the callback still re-checks the currently
    active issuer trust. ``jwks_uri`` is a configured reference to the trusted
    key set, not a key set itself; no key material is held here.
    """

    issuer: str
    authorization_endpoint: str
    client_id: str
    redirect_uri: str
    scopes: tuple[str, ...]
    token_endpoint: str
    jwks_uri: str
    allowed_signing_algorithms: tuple[str, ...]
    clock_skew: timedelta

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
        # Both verification URLs follow the issuer rules: a path and a port are
        # useful, a query would collide with the request parameters, and a
        # fragment is meaningless server-side. Neither is derived from the
        # issuer or the authorization endpoint, and neither is fetched here.
        _require_https_url(self.token_endpoint, "token_endpoint", allow_query=False)
        _require_https_url(self.jwks_uri, "jwks_uri", allow_query=False)
        self._validate_allowed_signing_algorithms()
        self._validate_clock_skew()

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

    def _validate_allowed_signing_algorithms(self) -> None:
        """Validate the allowlist without ever completing or reordering it.

        This is an **allowlist**, not a dynamic algorithm choice. A token's JOSE
        header may later select which of these applies; it must never extend the
        list, and a later adapter may only accept the intersection of this
        allowlist with the secure algorithms it supports built in. Nothing is
        added here: no RS256 and no other algorithm appears unless it was
        configured, because a silently completed list would grant an algorithm
        nobody approved.

        ``none`` is refused in any spelling. It is the unsigned JWT algorithm,
        so allowing it would turn every signature check into a no-op — the
        classic JWT bypass. The check is the one deliberate case-insensitive
        comparison in this model; values are otherwise never normalized, and the
        configured spelling is kept exactly.
        """

        if not isinstance(self.allowed_signing_algorithms, tuple):
            raise ValueError("allowed_signing_algorithms must be a tuple")
        if not self.allowed_signing_algorithms:
            raise ValueError("allowed_signing_algorithms must not be empty")
        seen: set[str] = set()
        for algorithm in self.allowed_signing_algorithms:
            if not isinstance(algorithm, str):
                raise ValueError("each signing algorithm must be a string")
            if not algorithm:
                raise ValueError("signing algorithm must not be empty")
            # A JOSE "alg" value is a bare token; whitespace would mean the
            # configured entry could never match a real header.
            if any(character.isspace() for character in algorithm):
                raise ValueError("signing algorithm must not contain whitespace")
            if algorithm.lower() == "none":
                raise ValueError("signing algorithm none is not allowed")
            if algorithm in seen:
                raise ValueError("allowed_signing_algorithms must not repeat")
            seen.add(algorithm)

    def _validate_clock_skew(self) -> None:
        """Bound the tolerated clock skew explicitly and keep it exact."""

        if not isinstance(self.clock_skew, timedelta):
            raise ValueError("clock_skew must be a timedelta")
        if self.clock_skew < timedelta(0):
            raise ValueError("clock_skew must not be negative")
        # An upper bound is a security rule, not a convenience: skew widens the
        # window in which an expired or not-yet-valid token still passes.
        if self.clock_skew > MAXIMUM_CLOCK_SKEW:
            raise ValueError("clock_skew must not exceed five minutes")
