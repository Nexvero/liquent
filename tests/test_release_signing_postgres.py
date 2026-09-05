from pathlib import Path

from sqlalchemy import Engine, text

from liquent_platform.identity.release_authority import (
    ReleasePolicyRevisionId,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseSignerAuthorityId,
    ReleaseSigningPublicKey,
)
from liquent_platform.persistence.release_key_activation import DatabaseReleaseKeyActivation
from liquent_platform.persistence.release_registry_bootstrap import (
    DatabaseInitialReleaseRegistryBootstrap,
)
from test_operational_release_bundle import _build
from test_release_signing import (
    ACTIVE,
    DECISION,
    FINGERPRINT,
    INITIAL,
    KEY,
    PUBLIC_KEY,
    Approval,
    Proof,
    _store,
)


def test_postgresql_commits_one_current_authority_bound_signing_decision(
    postgres_engine: Engine, tmp_path: Path,
) -> None:
    bootstrap = DatabaseInitialReleaseRegistryBootstrap(
        postgres_engine,
        generate_lifecycle_authority_id=lambda: ReleaseRegistryLifecycleAuthorityId("lifecycle-245"),
        generate_signer_authority_id=lambda: ReleaseSignerAuthorityId("signer-245"),
        generate_key_id=lambda: KEY,
        generate_registry_revision_id=lambda: INITIAL,
        generate_policy_revision_id=lambda: ReleasePolicyRevisionId("policy-245"),
    ).bootstrap(
        ReleaseRegistryBootstrapId("bootstrap-245"),
        ReleaseSigningPublicKey(FINGERPRINT, PUBLIC_KEY),
    )
    assert bootstrap is not None
    assert DatabaseReleaseKeyActivation(
        postgres_engine,
        proof_verifier=Proof(),
        approval_verifier=Approval(),
        generate_revision_id=lambda: ACTIVE,
    ).activate_key(
        ReleaseRegistryLifecycleChangeId("activation-245"),
        bootstrap.lifecycle_authority_id,
        KEY,
        INITIAL,
        b"proof",
        b"approval",
    ) is not None

    result = _store(postgres_engine).sign_candidate(
        DECISION, KEY, ACTIVE, str(_build(tmp_path / "candidate"))
    )

    assert result is not None
    with postgres_engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM release_signing_decisions"
        )) == 1
