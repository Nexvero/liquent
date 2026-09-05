import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.oidc_trust_authority import (
    DatabaseOidcTrustManagementAuthority,
)

pytestmark = pytest.mark.postgres_integration


def test_committed_oidc_trust_authority_revocation_is_current(
    postgres_engine: Engine,
) -> None:
    actor = UserId("actor-199")
    with postgres_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:actor,'active')"),
            {"actor": str(actor).encode()},
        )
        connection.execute(
            text(
                "INSERT INTO oidc_trust_management_authorities"
                " VALUES (:actor,'active')"
            ),
            {"actor": str(actor).encode()},
        )
    lookup = DatabaseOidcTrustManagementAuthority(postgres_engine)
    principal = SessionPrincipal(actor)
    assert lookup.permits_oidc_trust_management(principal) is True

    with postgres_engine.begin() as connection:
        connection.execute(
            text("UPDATE oidc_trust_management_authorities SET status='inactive'")
        )

    assert lookup.permits_oidc_trust_management(principal) is False
