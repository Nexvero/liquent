from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_authority import (
    ReleasePolicyRevisionId,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistrySetRevisionId,
    ReleaseSignerAuthorityId,
    ReleaseSigningKeyId,
    ReleaseSigningPublicKey,
)
from liquent_platform.persistence.release_registry_bootstrap import (
    DatabaseInitialReleaseRegistryBootstrap,
)


pytestmark = pytest.mark.postgres_integration
PUBLIC_KEY = ReleaseSigningPublicKey(
    "SHA256:" + "C" * 43,
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPostgresBootstrapKey",
)


def _store(engine: Engine, suffix: str) -> DatabaseInitialReleaseRegistryBootstrap:
    return DatabaseInitialReleaseRegistryBootstrap(
        engine,
        generate_lifecycle_authority_id=lambda: ReleaseRegistryLifecycleAuthorityId(
            f"lifecycle-{suffix}"
        ),
        generate_signer_authority_id=lambda: ReleaseSignerAuthorityId(
            f"signer-{suffix}"
        ),
        generate_key_id=lambda: ReleaseSigningKeyId(f"key-{suffix}"),
        generate_registry_revision_id=lambda: ReleaseRegistrySetRevisionId(
            f"revision-{suffix}"
        ),
        generate_policy_revision_id=lambda: ReleasePolicyRevisionId(
            f"policy-{suffix}"
        ),
    )


def test_concurrent_distinct_bootstraps_commit_exactly_one_complete_registry(
    postgres_engine: Engine,
) -> None:
    def bootstrap(suffix: str):
        return _store(postgres_engine, suffix).bootstrap(
            ReleaseRegistryBootstrapId(f"bootstrap-{suffix}"), PUBLIC_KEY
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(bootstrap, ("one", "two")))

    assert sum(result is not None for result in results) == 1
    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT "
            "(SELECT count(*) FROM release_registry_bootstraps),"
            "(SELECT count(*) FROM release_registry_set_revisions),"
            "(SELECT count(*) FROM release_registry_current_set),"
            "(SELECT count(*) FROM release_signing_keys),"
            "(SELECT count(*) FROM release_signing_decisions)"
        )).one() == (1, 1, 1, 1, 0)
        assert connection.execute(text(
            "SELECT signer.status,lifecycle.status,key.status "
            "FROM release_registry_current_set AS current "
            "JOIN release_registry_revision_signers AS signer "
            "ON signer.revision_id=current.revision_id "
            "JOIN release_registry_revision_lifecycle_authorities AS lifecycle "
            "ON lifecycle.revision_id=current.revision_id "
            "JOIN release_registry_revision_keys AS key "
            "ON key.revision_id=current.revision_id"
        )).one() == ("active", "active", "inactive")


def test_exact_retry_resolves_same_postgresql_decision(
    postgres_engine: Engine,
) -> None:
    bootstrap_id = ReleaseRegistryBootstrapId("bootstrap-retry")
    first = _store(postgres_engine, "retry").bootstrap(bootstrap_id, PUBLIC_KEY)
    second = _store(postgres_engine, "unused").bootstrap(bootstrap_id, PUBLIC_KEY)

    assert first is not None
    assert second == first
