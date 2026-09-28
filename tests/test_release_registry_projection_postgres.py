import json

import pytest
from sqlalchemy import Engine

from liquent_platform.identity.release_authority import (
    ReleasePolicyRevisionId,
    ReleasePromotionVerifierId,
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
from liquent_platform.persistence.release_registry_projection import (
    DatabaseCurrentReleaseAuthorityRegistryProjection,
)
from tools.release_promotion_verifier import _registry


pytestmark = pytest.mark.postgres_integration


def test_postgresql_projects_one_complete_repeatable_read_snapshot(
    postgres_engine: Engine,
) -> None:
    public_key = ReleaseSigningPublicKey(
        "SHA256:" + "G" * 43,
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPostgresProjectionKey",
    )
    bootstrap = DatabaseInitialReleaseRegistryBootstrap(
        postgres_engine,
        generate_lifecycle_authority_id=lambda: ReleaseRegistryLifecycleAuthorityId(
            "Lifecycle_PG_243"
        ),
        generate_signer_authority_id=lambda: ReleaseSignerAuthorityId(
            "Signer_PG_243"
        ),
        generate_key_id=lambda: ReleaseSigningKeyId("Key_PG_243"),
        generate_registry_revision_id=lambda: ReleaseRegistrySetRevisionId(
            "Revision_PG_243"
        ),
        generate_policy_revision_id=lambda: ReleasePolicyRevisionId("Policy_PG_243"),
    )
    assert bootstrap.bootstrap(
        ReleaseRegistryBootstrapId("Bootstrap_PG_243"), public_key
    ) is not None

    value = DatabaseCurrentReleaseAuthorityRegistryProjection(
        postgres_engine,
        verification_identity=ReleasePromotionVerifierId("Verifier_PG_243"),
    ).project()

    assert value is not None
    parsed = _registry(value)
    assert parsed == json.loads(value)
    assert parsed["authorities"][0]["keys"][0]["status"] == "inactive"
