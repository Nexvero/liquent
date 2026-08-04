"""Start one server-side OIDC login transaction without any transport."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from liquent_platform.application.oidc_login_errors import (
    OidcLoginStartConflict,
)
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.oidc_login_material import (
    SecureOidcLoginMaterialGenerator,
)
from liquent_platform.identity.oidc_login_transaction import (
    OidcLoginState,
    PendingOidcLoginTransaction,
)
from liquent_platform.identity.ports import OidcLoginTransactionCreationStore


@dataclass(frozen=True, slots=True)
class StartedOidcLogin:
    """Exactly the public material the later authorization request needs.

    The ``code_verifier`` stays behind in the server-side pending record and is
    deliberately absent here, as is the ``admission_id``: the admission binding
    is resolved server-side at callback time and must never travel with the
    browser. The object carries no tokens, claims, user, workspace, role, or
    Liquent session data, and it builds no authorization URL.

    ``state`` and ``nonce`` must reach the browser to be usable, but they remain
    sensitive login-correlation values and are hidden from ``repr`` so they
    cannot leak through logs or error diagnostics. The ``code_challenge`` is not
    a secret and may appear in ``repr``. All three values are taken verbatim
    from the generated material and nothing is normalized or derived; the
    fields are validated by ``OidcLoginMaterial`` and not re-checked here.
    """

    state: str = field(repr=False)
    nonce: str = field(repr=False)
    code_challenge: str


def start_oidc_login(
    store: OidcLoginTransactionCreationStore,
    generator: SecureOidcLoginMaterialGenerator,
    *,
    expected_issuer: str,
    redirect_uri: str,
    now: datetime,
    lifetime: timedelta,
    admission_id: IdentityAdmissionId | None = None,
    return_path: str | None = None,
) -> StartedOidcLogin:
    """Generate one login transaction and store it atomically, or conflict.

    The clock is injected: this use case reads no system time, and the record
    expires exactly at ``now + lifetime``. Both time bounds are checked before
    any material is drawn, so an invalid call neither generates secrets nor
    touches the store. Every other field invariant is left to
    ``PendingOidcLoginTransaction``; in particular no URL, redirect, or return
    path safety rule is decided here, and no upper bound is placed on the
    lifetime in this slice.

    The material is generated exactly once and the store is called exactly
    once. A neutral False is a conflict and never a partial success: nothing is
    retried, no second state is drawn, and the caller learns nothing about the
    colliding state. A failing store raises its own error unchanged rather than
    being reinterpreted as a conflict.

    Issuer trust, discovery, tokens, claims, admission validation, workspace
    membership, and Liquent session creation all stay outside this slice.
    """

    if lifetime <= timedelta(0):
        raise ValueError("login transaction lifetime must be positive")
    # Checked here and not only by the record, so that a naive clock is
    # rejected before any secret is generated.
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    material = generator.new_login_material()
    pending = PendingOidcLoginTransaction(
        expected_issuer=expected_issuer,
        expected_nonce=material.nonce,
        code_verifier=material.code_verifier,
        redirect_uri=redirect_uri,
        created_at=now,
        expires_at=now + lifetime,
        admission_id=admission_id,
        return_path=return_path,
    )
    if not store.add_transaction(OidcLoginState(material.state), pending):
        raise OidcLoginStartConflict
    return StartedOidcLogin(
        material.state,
        material.nonce,
        material.code_challenge,
    )
