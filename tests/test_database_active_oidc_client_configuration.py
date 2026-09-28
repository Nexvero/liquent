from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.ports import ActiveOidcClientConfigurationLookup
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    OidcClientConfigurationStoreUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.oidc_client_configuration import (
    DatabaseActiveOidcClientConfiguration,
)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'oidc-configuration.db'}")
    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _insert(
    engine: Engine, *, active: bool = True, revision: bytes | None = None
) -> None:
    with engine.begin() as connection:
        if revision is not None:
            connection.execute(
                text(
                    "INSERT INTO oidc_trust_revisions"
                    " (revision_id,issuer,authorization_endpoint,client_id,"
                    " redirect_uri,scopes,token_endpoint,jwks_uri,"
                    " allowed_signing_algorithms,clock_skew_microseconds) VALUES"
                    " (:revision,:issuer,:authorization,:client,:redirect,:scopes,"
                    " :token,:jwks,:algorithms,:skew)"
                ),
                {
                    "revision": revision,
                    "issuer": b"https://issuer.example/exact",
                    "authorization": b"https://issuer.example/authorize",
                    "client": b"client-192",
                    "redirect": b"https://app.example/callback?fixed=1",
                    "scopes": b'["openid","profile"]',
                    "token": b"https://issuer.example/token",
                    "jwks": b"https://issuer.example/keys",
                    "algorithms": b'["RS256","ES256"]',
                    "skew": 45_000_000,
                },
            )
        connection.execute(
            text(
                "INSERT INTO oidc_client_configuration"
                " (singleton_key,active,issuer,authorization_endpoint,client_id,"
                " redirect_uri,scopes,token_endpoint,jwks_uri,"
                " allowed_signing_algorithms,clock_skew_microseconds,revision_id) VALUES"
                " (1,:active,:issuer,:authorization,:client,:redirect,:scopes,"
                " :token,:jwks,:algorithms,:skew,:revision)"
            ),
            {
                "active": active,
                "issuer": b"https://issuer.example/exact",
                "authorization": b"https://issuer.example/authorize",
                "client": b"client-192",
                "redirect": b"https://app.example/callback?fixed=1",
                "scopes": b'["openid","profile"]',
                "token": b"https://issuer.example/token",
                "jwks": b"https://issuer.example/keys",
                "algorithms": b'["RS256","ES256"]',
                "skew": 45_000_000,
                "revision": revision,
            },
        )


def test_empty_store_is_neutral_absence(engine: Engine) -> None:
    lookup: ActiveOidcClientConfigurationLookup = (
        DatabaseActiveOidcClientConfiguration(engine)
    )
    assert lookup.get_active_configuration() is None


def test_inactive_store_is_neutral_absence(engine: Engine) -> None:
    _insert(engine, active=False)
    lookup = DatabaseActiveOidcClientConfiguration(engine)
    assert lookup.get_active_configuration() is None


def test_active_configuration_is_restored_exactly(engine: Engine) -> None:
    _insert(engine)
    lookup = DatabaseActiveOidcClientConfiguration(engine)
    assert lookup.get_active_configuration() == TrustedOidcClientConfiguration(
        issuer="https://issuer.example/exact",
        authorization_endpoint="https://issuer.example/authorize",
        client_id="client-192",
        redirect_uri="https://app.example/callback?fixed=1",
        scopes=("openid", "profile"),
        token_endpoint="https://issuer.example/token",
        jwks_uri="https://issuer.example/keys",
        allowed_signing_algorithms=("RS256", "ES256"),
        clock_skew=timedelta(seconds=45),
    )


def test_active_trust_binds_the_exact_persistent_revision(engine: Engine) -> None:
    _insert(engine, revision=b"trust-revision-201")

    trust = DatabaseActiveOidcClientConfiguration(engine).get_active_trust()

    assert trust is not None
    assert trust.revision_id.value == "trust-revision-201"
    assert trust.configuration.client_id == "client-192"


def test_active_configuration_without_revision_is_unavailable_as_trust(
    engine: Engine,
) -> None:
    _insert(engine)

    with pytest.raises(OidcClientConfigurationStoreUnavailable):
        DatabaseActiveOidcClientConfiguration(engine).get_active_trust()


def test_later_deactivation_affects_later_lookup(engine: Engine) -> None:
    _insert(engine)
    lookup = DatabaseActiveOidcClientConfiguration(engine)
    assert lookup.get_active_configuration() is not None
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE oidc_client_configuration SET active=false")
        )
    assert lookup.get_active_configuration() is None


def test_malformed_active_record_is_technical_unavailability(engine: Engine) -> None:
    _insert(engine)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE oidc_client_configuration SET scopes=:scopes"),
            {"scopes": b"not-json"},
        )
    lookup = DatabaseActiveOidcClientConfiguration(engine)
    with pytest.raises(OidcClientConfigurationStoreUnavailable) as raised:
        lookup.get_active_configuration()
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_unmigrated_store_is_detail_free_technical_unavailability(
    tmp_path: Path,
) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    lookup = DatabaseActiveOidcClientConfiguration(engine)
    try:
        with pytest.raises(OidcClientConfigurationStoreUnavailable) as raised:
            lookup.get_active_configuration()
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(lookup) == "DatabaseActiveOidcClientConfiguration()"
    finally:
        engine.dispose()


def test_singleton_constraint_prevents_a_second_configuration(engine: Engine) -> None:
    _insert(engine)
    with pytest.raises(Exception):
        _insert(engine)
