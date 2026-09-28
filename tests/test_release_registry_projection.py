import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.release_authority import (
    ReleaseActivationReviewerId,
    ReleasePolicyRevisionId,
    ReleasePromotionVerifierId,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistryLifecycleChangeId,
    ReleaseRegistrySetRevisionId,
    ReleaseSignerAuthorityId,
    ReleaseSigningKeyId,
    ReleaseSigningPublicKey,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    ReleaseRegistryProjectionUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.release_key_activation import DatabaseReleaseKeyActivation
from liquent_platform.persistence.release_registry_bootstrap import (
    DatabaseInitialReleaseRegistryBootstrap,
)
from liquent_platform.persistence.release_registry_projection import (
    DatabaseCurrentReleaseAuthorityRegistryProjection,
)
from tools.release_promotion_verifier import _registry


ACTOR = ReleaseRegistryLifecycleAuthorityId("Lifecycle_243")
SIGNER = ReleaseSignerAuthorityId("Signer_243")
KEY = ReleaseSigningKeyId("Key_243")
INITIAL = ReleaseRegistrySetRevisionId("Revision_241")
ACTIVE = ReleaseRegistrySetRevisionId("Revision_242")
PUBLIC_KEY = ReleaseSigningPublicKey(
    "SHA256:" + "F" * 43,
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIProjectionKey",
)


class Proof:
    def verify_proof(self, public_key, challenge, proof):
        return True


class Approval:
    def verify_approval(self, challenge, approval):
        return ReleaseActivationReviewerId("Reviewer_243")


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'projection.db'}")

    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _projection(engine):
    return DatabaseCurrentReleaseAuthorityRegistryProjection(
        engine, verification_identity=ReleasePromotionVerifierId("Verifier_243")
    )


def _bootstrap(engine):
    store = DatabaseInitialReleaseRegistryBootstrap(
        engine,
        generate_lifecycle_authority_id=lambda: ACTOR,
        generate_signer_authority_id=lambda: SIGNER,
        generate_key_id=lambda: KEY,
        generate_registry_revision_id=lambda: INITIAL,
        generate_policy_revision_id=lambda: ReleasePolicyRevisionId("Policy_243"),
    )
    return store.bootstrap(ReleaseRegistryBootstrapId("Bootstrap_243"), PUBLIC_KEY)


def test_absent_current_registry_is_neutral_and_parameterless(engine: Engine):
    projection = _projection(engine)
    assert projection.project() is None
    assert repr(projection) == "DatabaseCurrentReleaseAuthorityRegistryProjection()"


def test_bootstrap_projection_is_canonical_and_accepted_by_lq238(engine: Engine):
    assert _bootstrap(engine) is not None

    value = _projection(engine).project()
    assert value is not None
    parsed = json.loads(value)
    assert value == (
        json.dumps(parsed, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")
    assert _registry(value) == parsed
    assert parsed["policy_revision"] == "Policy_243"
    assert parsed["verification_identity"] == "Verifier_243"
    assert parsed["authorities"] == [{
        "authority_id": "Signer_243",
        "status": "active",
        "keys": [{
            "key_id": "Key_243",
            "status": "inactive",
            "fingerprint": PUBLIC_KEY.fingerprint,
            "algorithm": "ssh-ed25519",
            "namespaces": ["liquent-operations-release-v1"],
            "public_key": PUBLIC_KEY.public_key,
        }],
    }]


def test_each_call_observes_later_committed_key_activation(engine: Engine):
    assert _bootstrap(engine) is not None
    projection = _projection(engine)
    assert json.loads(projection.project())["authorities"][0]["keys"][0][
        "status"
    ] == "inactive"
    activation = DatabaseReleaseKeyActivation(
        engine,
        proof_verifier=Proof(),
        approval_verifier=Approval(),
        generate_revision_id=lambda: ACTIVE,
    )
    assert activation.activate_key(
        ReleaseRegistryLifecycleChangeId("Activation_243"),
        ACTOR,
        KEY,
        INITIAL,
        b"proof",
        b"approval",
    ) is not None
    assert json.loads(projection.project())["authorities"][0]["keys"][0][
        "status"
    ] == "active"


def test_incomplete_current_snapshot_is_detail_free_unavailable(engine: Engine):
    assert _bootstrap(engine) is not None
    with engine.begin() as connection:
        connection.execute(text(
            "DELETE FROM release_registry_revision_keys WHERE revision_id=:revision"
        ), {"revision": INITIAL.value.encode()})

    with pytest.raises(ReleaseRegistryProjectionUnavailable) as raised:
        _projection(engine).project()
    assert raised.value.args == ("release_registry_projection_unavailable",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_unmigrated_projection_is_detail_free(tmp_path: Path):
    engine = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    try:
        with pytest.raises(ReleaseRegistryProjectionUnavailable):
            _projection(engine).project()
    finally:
        engine.dispose()
