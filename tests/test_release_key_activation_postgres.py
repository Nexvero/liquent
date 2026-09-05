from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_authority import (
    ReleaseActivationReviewerId,
    ReleasePolicyRevisionId,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseRegistrySetRevisionId,
    ReleaseSignerAuthorityId,
    ReleaseSigningKeyId,
    ReleaseSigningPublicKey,
)
from liquent_platform.persistence.release_key_activation import DatabaseReleaseKeyActivation
from liquent_platform.persistence.release_registry_bootstrap import (
    DatabaseInitialReleaseRegistryBootstrap,
)


pytestmark = pytest.mark.postgres_integration
ACTOR = ReleaseRegistryLifecycleAuthorityId("lifecycle-pg-242")
KEY = ReleaseSigningKeyId("key-pg-242")
INITIAL = ReleaseRegistrySetRevisionId("initial-pg-242")
PUBLIC_KEY = ReleaseSigningPublicKey(
    "SHA256:" + "E" * 43,
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPostgresActivationKey",
)


class Proof:
    def verify_proof(self, public_key, challenge, proof):
        return public_key == PUBLIC_KEY.public_key and bool(challenge) and proof == b"proof"


class Approval:
    def verify_approval(self, challenge, approval):
        if challenge and approval == b"approval":
            return ReleaseActivationReviewerId("independent-pg-reviewer")
        return None


def test_concurrent_activations_against_one_revision_commit_once(
    postgres_engine: Engine,
) -> None:
    bootstrap = DatabaseInitialReleaseRegistryBootstrap(
        postgres_engine,
        generate_lifecycle_authority_id=lambda: ACTOR,
        generate_signer_authority_id=lambda: ReleaseSignerAuthorityId("signer-pg-242"),
        generate_key_id=lambda: KEY,
        generate_registry_revision_id=lambda: INITIAL,
        generate_policy_revision_id=lambda: ReleasePolicyRevisionId("policy-pg-242"),
    )
    assert bootstrap.bootstrap(
        ReleaseRegistryBootstrapId("bootstrap-pg-242"), PUBLIC_KEY
    ) is not None

    def activate(suffix: str):
        store = DatabaseReleaseKeyActivation(
            postgres_engine,
            proof_verifier=Proof(),
            approval_verifier=Approval(),
            generate_revision_id=lambda: ReleaseRegistrySetRevisionId(
                f"activated-{suffix}"
            ),
        )
        return store.activate_key(
            ReleaseRegistryLifecycleChangeId(f"change-{suffix}"),
            ACTOR,
            KEY,
            INITIAL,
            b"proof",
            b"approval",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(activate, ("one", "two")))

    assert sum(result is not None for result in results) == 1
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM release_key_activations"
        )) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM release_registry_lifecycle_changes"
        )) == 1
        assert connection.execute(text(
            "SELECT keys.status FROM release_registry_current_set AS current "
            "JOIN release_registry_revision_keys AS keys "
            "ON keys.revision_id=current.revision_id"
        )).scalar_one() == "active"
