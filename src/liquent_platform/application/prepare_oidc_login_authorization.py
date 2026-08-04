"""Connect the three login-start steps into one transport-free use case."""

from datetime import datetime, timedelta

from liquent_platform.application.build_oidc_authorization_request import (
    OidcAuthorizationRequest,
    build_oidc_authorization_request,
)
from liquent_platform.application.oidc_login_errors import OidcLoginUnavailable
from liquent_platform.application.start_oidc_login import start_oidc_login
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.oidc_login_material import (
    SecureOidcLoginMaterialGenerator,
)
from liquent_platform.identity.ports import (
    ActiveOidcClientConfigurationLookup,
    OidcLoginTransactionCreationStore,
)


def prepare_oidc_login_authorization(
    configuration_lookup: ActiveOidcClientConfigurationLookup,
    transaction_store: OidcLoginTransactionCreationStore,
    generator: SecureOidcLoginMaterialGenerator,
    *,
    now: datetime,
    lifetime: timedelta,
    admission_id: IdentityAdmissionId | None = None,
    return_path: str | None = None,
) -> OidcAuthorizationRequest:
    """Read the active configuration once, start the login, and shape the request.

    The signature accepts no issuer, authorization endpoint, client id,
    redirect uri, scope, provider, tenant, workspace, user, or transport value.
    All of those come solely from the configuration lookup, so no caller can
    steer which provider a login goes to.

    The configuration is read **exactly once** and that one object feeds both
    the pending record and the authorization request, so a single start can
    never mix two configurations: the stored ``expected_issuer`` and
    ``redirect_uri`` always belong to the same snapshot as the request's
    endpoint, client id, redirect uri, and scopes. Two separate calls may each
    read a newer snapshot.

    A missing active configuration raises the neutral OidcLoginUnavailable
    before the generator, the store, or the builder is touched — no fallback
    configuration is chosen and nothing is retried.

    Time validation stays with ``start_oidc_login`` and is not duplicated here.
    An invalid ``now`` or ``lifetime`` can therefore happen after the read-only
    lookup already ran; the generator and the store still stay untouched,
    because LQ-144 validates before drawing material. The order is deliberate.

    Every other failure propagates unchanged and is never reinterpreted: a
    lookup infrastructure error does not become OidcLoginUnavailable or None, a
    creation conflict stays OidcLoginStartConflict and stops before the builder
    so no partial request is returned, and store, generator, and builder errors
    surface as they are. No error message of this use case carries an issuer,
    endpoint, client id, redirect uri, state, nonce, code challenge, admission
    id, or return path.

    The use case makes no issuer trust decision of its own, re-validates
    nothing, freezes no trust status, runs no discovery, loads no signing keys,
    and inspects no tokens or claims. The callback must still re-check the
    current issuer trust: an issuer disabled between start and callback ends
    the callback neutrally.
    """

    configuration = configuration_lookup.get_active_configuration()
    if configuration is None:
        raise OidcLoginUnavailable

    started = start_oidc_login(
        transaction_store,
        generator,
        expected_issuer=configuration.issuer,
        redirect_uri=configuration.redirect_uri,
        now=now,
        lifetime=lifetime,
        admission_id=admission_id,
        return_path=return_path,
    )
    # Built only after the transaction was stored, from the very same
    # configuration object the lookup returned.
    return build_oidc_authorization_request(configuration, started)
