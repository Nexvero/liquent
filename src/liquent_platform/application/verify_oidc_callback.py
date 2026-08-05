"""Claim one login transaction and verify its callback, without any transport."""

from dataclasses import dataclass, field

from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.external_identity import ExternalIdentity
from liquent_platform.identity.oidc_login_transaction import OidcLoginState
from liquent_platform.identity.oidc_verification import (
    OidcAuthorizationCodeVerification,
)
from liquent_platform.identity.ports import (
    OidcAuthorizationCodeVerifier,
    OidcLoginTransactionClaimStore,
)


@dataclass(frozen=True, slots=True)
class VerifiedOidcCallback:
    """Exactly what a later completion boundary needs, and nothing else.

    All three values are hidden from ``repr``: the identity can carry a
    personal external identifier, the admission id is a capability handle, and
    the return path is internal navigation metadata. ``ExternalIdentity`` does
    not hide its own fields, so hiding this one is what keeps the issuer and
    subject out of an object representation.

    The object carries no state, authorization code, nonce, code verifier,
    token, configuration value, or session material, and it grants nothing.
    """

    identity: ExternalIdentity = field(repr=False)
    admission_id: IdentityAdmissionId | None = field(repr=False)
    return_path: str | None = field(repr=False)


def verify_oidc_callback(
    transaction_store: OidcLoginTransactionClaimStore,
    verifier: OidcAuthorizationCodeVerifier,
    state: OidcLoginState,
    authorization_code: str | None,
) -> VerifiedOidcCallback | None:
    """Run the post-binding callback steps in their one permitted order.

    The caller has already read the query duplicate-safely, determined exactly
    one non-empty state, compared it against the binding cookie in constant
    time, and aborted neutrally on a missing or mismatching cookie. Nothing has
    been claimed yet. This use case therefore takes no clock and no HTTP,
    cookie, or request value.

    ``authorization_code=None`` means only that the duplicate-safe transport
    parser recognized a valid provider-error form. Malformed query shapes must
    never reach this use case, and the provider's error, error_description, and
    error_uri deliberately are not parameters: they must not cross the
    transport boundary at all.

    The transaction is claimed **first and exactly once**, before anything
    external happens. A neutral None from the store unifies unknown, expired,
    and already consumed, and ends the call without touching the verifier. From
    that point on the transaction stays consumed on every path: there is no
    retry, no second claim, and no store rollback, because any of those would
    be a replay path.

    A present code must be a real non-empty string. Should a direct caller
    ignore the transport contract, the transaction has already been claimed
    fail-closed, so the call ends neutrally without reaching the verifier and
    without an exception that could carry the code. Nothing is trimmed,
    normalized, or logged.

    The verification input is built solely from the query code and the four
    verification-relevant values of the claimed record; no active configuration
    and no browser value is mixed in. The verifier runs exactly once. Its None
    becomes None here, an OidcVerificationUnavailable propagates unchanged, and
    an identity becomes the success result.

    Success means only that this external identity was verified for exactly
    this transaction. It resolves no UserId, consumes no admission, grants no
    membership or role, and creates no session, CSRF value, or redirect.
    """

    transaction = transaction_store.claim_transaction(state)
    if transaction is None:
        # Unknown, expired, or already consumed — indistinguishable on purpose.
        return None
    if authorization_code is None:
        # Valid provider-error form: consumed, but never redeemed.
        return None
    if not isinstance(authorization_code, str) or not authorization_code:
        # Excluded by the transport contract; still fail closed rather than
        # hand an unusable value to the verifier.
        return None

    verification = OidcAuthorizationCodeVerification(
        authorization_code=authorization_code,
        expected_issuer=transaction.expected_issuer,
        expected_nonce=transaction.expected_nonce,
        code_verifier=transaction.code_verifier,
        redirect_uri=transaction.redirect_uri,
    )
    # OidcVerificationUnavailable is deliberately not caught: technical
    # unavailability is not a business rejection and must stay distinguishable
    # for the caller.
    identity = verifier.verify_authorization_code(verification)
    if identity is None:
        return None
    # Both values come verbatim from the claimed record, never from the browser.
    return VerifiedOidcCallback(
        identity, transaction.admission_id, transaction.return_path
    )
