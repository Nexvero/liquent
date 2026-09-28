from __future__ import annotations

import threading
from datetime import timedelta

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.oidc_client_configuration import (
    TrustedOidcClientConfiguration,
)
from liquent_platform.identity.oidc_trust import (
    OidcTrustChangeId,
    OidcTrustChangeKind,
    OidcTrustRevisionId,
)
from liquent_platform.identity.session import SessionPrincipal
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.oidc_trust_changes import (
    DatabaseAuthorizedOidcTrustChanges,
)

pytestmark = pytest.mark.postgres_integration

ACTOR = UserId("actor-202-postgres")
CHANGE = OidcTrustChangeId("change-202-postgres")
CONFIGURATION = TrustedOidcClientConfiguration(
    issuer="https://idp.example",
    authorization_endpoint="https://idp.example/authorize",
    client_id="client",
    redirect_uri="https://app.example/callback",
    scopes=("openid",),
    token_endpoint="https://idp.example/token",
    jwks_uri="https://idp.example/jwks",
    allowed_signing_algorithms=("RS256",),
    clock_skew=timedelta(seconds=30),
)


def test_concurrent_exact_activation_converges_on_one_revision(
    postgres_engine: Engine, postgres_url: str
) -> None:
    with postgres_engine.begin() as connection:
        connection.execute(
            text("INSERT INTO identity_users VALUES (:actor,'active')"),
            {"actor": ACTOR.encode()},
        )
        connection.execute(
            text(
                "INSERT INTO oidc_trust_management_authorities"
                " VALUES (:actor,'active')"
            ),
            {"actor": ACTOR.encode()},
        )
    start = threading.Barrier(2)
    outcomes: list[object] = []
    guard = threading.Lock()

    def attempt(name: str) -> None:
        engine = build_engine(postgres_url)
        try:
            store = DatabaseAuthorizedOidcTrustChanges(
                engine,
                generate_revision_id=lambda: OidcTrustRevisionId(
                    f"revision-{name}"
                ),
            )
            start.wait(timeout=15)
            outcome: object = store.change_trust(
                CHANGE, SessionPrincipal(ACTOR), OidcTrustChangeKind.ACTIVATE,
                None, CONFIGURATION,
            )
        except Exception as error:
            outcome = error
        finally:
            engine.dispose()
        with guard:
            outcomes.append(outcome)

    threads = [threading.Thread(target=attempt, args=(name,)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert [thread.is_alive() for thread in threads] == [False, False]
    assert not any(isinstance(outcome, Exception) for outcome in outcomes)
    assert len({outcome.revision_id for outcome in outcomes}) == 1  # type: ignore[union-attr]
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM oidc_trust_revisions")) == 1
        assert connection.scalar(text("SELECT count(*) FROM authorized_oidc_trust_changes")) == 1
