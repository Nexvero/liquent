"""Shape one OIDC authorization request from already validated inputs."""

from dataclasses import dataclass, field
from urllib.parse import urlencode

from liquent_platform.application.start_oidc_login import StartedOidcLogin
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)


@dataclass(frozen=True, slots=True)
class OidcAuthorizationRequest:
    """The finished authorization request URL, kept out of ``repr``.

    The URL carries ``state`` and ``nonce`` and must stay usable as a redirect
    target, so the value is hidden from ``repr`` instead of being weakened: an
    object representation must not carry it into logs or error diagnostics. The
    class name may appear; the URL and with it the state, nonce, client id,
    redirect URI, and code challenge must not. The value stays available through
    ``.url`` for the later authorized transport boundary.

    There are no separate parameter fields, and in particular no code verifier,
    admission handle, return path, token, claim, user, workspace, role, or
    session value.
    """

    url: str = field(repr=False)


def build_oidc_authorization_request(
    configuration: TrustedOidcClientConfiguration,
    started: StartedOidcLogin,
) -> OidcAuthorizationRequest:
    """Build the authorization request URL deterministically, without side effects.

    Both inputs are already validated: ``TrustedOidcClientConfiguration``
    guarantees an absolute https endpoint with a host and without userinfo,
    query, fragment, raw control characters, or an invalid port, and it
    guarantees a non-empty unique scope tuple containing ``openid``.
    ``StartedOidcLogin`` carries the generated material. None of that is
    re-validated here and no value is normalized or derived.

    Exactly nine parameters are emitted, each once, in a fixed order. Every key
    and value comes from ``urlencode`` over an ordered pair sequence, so a
    reserved character in a value — an ``&`` in the client id, an ``=`` in the
    state, a ``#`` in the nonce, or the fixed query of a redirect URI — is
    percent-encoded and can neither add, duplicate, nor override a mandatory
    parameter, and no fragment can appear. Because the validated endpoint has
    no query and no fragment, the encoded query is appended after a single
    ``?`` and the endpoint keeps its exact spelling; it is never rebuilt or
    re-canonicalized.

    Holding a ``TrustedOidcClientConfiguration`` only means some later calling
    boundary selected it. This builder makes no trust decision, reads no
    configuration, generates no material, stores nothing, performs no network
    call, and issues no redirect. The callback must still re-check the current
    issuer trust.
    """

    query = urlencode(
        [
            ("response_type", "code"),
            ("response_mode", "query"),
            ("client_id", configuration.client_id),
            ("redirect_uri", configuration.redirect_uri),
            ("scope", " ".join(configuration.scopes)),
            ("state", started.state),
            ("nonce", started.nonce),
            ("code_challenge", started.code_challenge),
            ("code_challenge_method", "S256"),
        ]
    )
    return OidcAuthorizationRequest(
        f"{configuration.authorization_endpoint}?{query}"
    )
