import pytest
from sqlalchemy import Engine, text

from liquent_platform.persistence.oidc_client_configuration import (
    DatabaseActiveOidcClientConfiguration,
)

pytestmark = pytest.mark.postgres_integration


def test_committed_deactivation_is_seen_by_later_lookup(
    postgres_engine: Engine,
) -> None:
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO oidc_client_configuration"
                " (singleton_key,active,issuer,authorization_endpoint,client_id,"
                " redirect_uri,scopes,token_endpoint,jwks_uri,"
                " allowed_signing_algorithms,clock_skew_microseconds) VALUES"
                " (1,true,:issuer,:authorization,:client,:redirect,:scopes,"
                " :token,:jwks,:algorithms,0)"
            ),
            {
                "issuer": b"https://issuer.example",
                "authorization": b"https://issuer.example/authorize",
                "client": b"client-192",
                "redirect": b"https://app.example/callback",
                "scopes": b'["openid"]',
                "token": b"https://issuer.example/token",
                "jwks": b"https://issuer.example/keys",
                "algorithms": b'["RS256"]',
            },
        )
    lookup = DatabaseActiveOidcClientConfiguration(postgres_engine)
    assert lookup.get_active_configuration() is not None

    with postgres_engine.begin() as connection:
        connection.execute(
            text("UPDATE oidc_client_configuration SET active=false")
        )

    assert lookup.get_active_configuration() is None
