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

    All three fields are repr-free — ``ExternalIdentity`` does not hide its own
    — so no identifier, capability handle, or navigation target reaches a log
    through an object representation. The result grants no permission and
    creates no session.
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
    """Claim the transaction fail-closed, then verify an optional code.

    Runs after a successful browser binding (LQ-158); it performs no transport
    and no completion work, so it takes no clock and no request value.
    ``authorization_code=None`` means the transport parser recognized a valid
    provider-error form.
    """

    # Claimed before anything external, so every later path leaves the
    # transaction consumed: no retry, no second claim, no rollback.
    transaction = transaction_store.claim_transaction(state)
    if transaction is None:
        # Unknown, expired, and already consumed are one neutral None.
        return None
    if authorization_code is None:
        # Valid provider-error form: consumed, but never redeemed.
        return None
    if not isinstance(authorization_code, str) or not authorization_code:
        # Excluded by the transport contract; still fail closed.
        return None

    verification = OidcAuthorizationCodeVerification(
        authorization_code=authorization_code,
        expected_issuer=transaction.expected_issuer,
        expected_nonce=transaction.expected_nonce,
        code_verifier=transaction.code_verifier,
        redirect_uri=transaction.redirect_uri,
    )
    # OidcVerificationUnavailable is deliberately not caught: technical
    # unavailability is not a business rejection.
    identity = verifier.verify_authorization_code(verification)
    if identity is None:
        return None
    return VerifiedOidcCallback(
        identity, transaction.admission_id, transaction.return_path
    )
