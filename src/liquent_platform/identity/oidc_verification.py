"""Input and neutral failure signal for the external OIDC verification boundary."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class OidcAuthorizationCodeVerification:
    """Everything the external verification boundary needs, and nothing more.

    This is the level-three input of LQ-155: the authorization code from the
    callback plus exactly the four verification-relevant values of a login
    transaction that has **already** been claimed atomically. It is assembled by
    the calling callback flow after the browser binding and the single-use
    claim have both succeeded.

    Deliberately absent, each for its own reason:

    - the ``state`` belongs to the browser binding and the atomic claim
      (levels one and two) and has no role in verifying a token; carrying it
      here would only widen the secret surface,
    - the ``admission_id`` is a capability handle that authorizes a one-time
      onboarding or binding operation, so a boundary whose only job is to
      **prove** an identity must be unable to carry or consume it,
    - the ``return_path`` is a transport concern of the calling flow,
    - the active trusted configuration — token endpoint, JWKS reference,
      allowed algorithms, clock skew (LQ-156) — is read again inside the later
      port implementation and never comes from a caller or a browser, so no
      caller can steer which provider a verification talks to.

    The object also carries no tokens, claims, subject, ExternalIdentity, user,
    workspace, role, session, or permission data, and it authorizes nothing.

    All five values are kept exactly and opaquely: no trimming, lowercasing,
    URL parsing, percent-decoding, or any other normalization. An authorization
    code and a redirect URI must reach the token endpoint byte for byte as they
    were issued and stored, and the nonce and verifier are compared and proven
    exactly.

    Every value is a short-lived secret or a sensitive correlation value, so all
    five are hidden from ``repr``: the representation reads
    ``OidcAuthorizationCodeVerification()`` and cannot carry any of them into
    logs or error diagnostics. The class name may appear.
    """

    authorization_code: str = field(repr=False)
    expected_issuer: str = field(repr=False)
    expected_nonce: str = field(repr=False)
    code_verifier: str = field(repr=False)
    redirect_uri: str = field(repr=False)

    def __post_init__(self) -> None:
        # Messages name the field but never echo the value, so a rejected input
        # cannot leak a code, verifier, or nonce through an error.
        if not self.authorization_code:
            raise ValueError("authorization_code must not be empty")
        if not self.expected_issuer:
            raise ValueError("expected_issuer must not be empty")
        if not self.expected_nonce:
            raise ValueError("expected_nonce must not be empty")
        if not self.code_verifier:
            raise ValueError("code_verifier must not be empty")
        if not self.redirect_uri:
            raise ValueError("redirect_uri must not be empty")


class OidcVerificationUnavailable(Exception):
    """Report that the external verification could not be carried out at all.

    This signals **technical unavailability only** — a configuration store that
    cannot be read, a network failure, an unreachable token endpoint or JWKS
    source, key verification that cannot be performed safely, or an internal
    adapter or library fault.

    A **business** rejection is not an error here: an untrusted or inactive
    issuer, a refused or invalid code, a missing or invalid token, a signature,
    algorithm, key, claim, audience, ``azp``, time, or nonce failure, and a
    missing or empty subject all resolve to a neutral ``None``. There is
    deliberately no second exception class for them, because a typed business
    failure would invite callers to branch on a cause that must stay
    indistinguishable.

    The error takes no constructor arguments and carries nothing beyond its
    neutral code: no authorization code, state, nonce, verifier, issuer,
    redirect URI, token, claim, provider text, or configuration detail. A later
    adapter must translate its internal failures into this error rather than
    letting one propagate that could carry such a value.

    Raising it says only "not right now" and reveals nothing about whether an
    identity, user, or configuration exists. How a later callback transport
    answers it — the same neutral status as a business rejection or a different
    one — is explicitly left to that contract (LQ-155 §12).
    """

    code = "oidc_verification_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)
