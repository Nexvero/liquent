from __future__ import annotations

import inspect
from pathlib import Path
from typing import Generic, TypeVar

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.ports import InitialReleaseRegistryBootstrap
from liquent_platform.identity.release_authority import (
    BootstrappedReleaseRegistry,
    ReleasePolicyRevisionId,
    ReleaseRegistryBootstrapId,
    ReleaseRegistryLifecycleAuthorityId,
    ReleaseRegistrySetRevisionId,
    ReleaseSignerAuthorityId,
    ReleaseSigningKeyId,
    ReleaseSigningPublicKey,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_errors import (
    ReleaseRegistryBootstrapConflict,
    ReleaseRegistryBootstrapUnavailable,
)
from liquent_platform.persistence.migrate import upgrade_to_head
from liquent_platform.persistence.release_registry_bootstrap import (
    DatabaseInitialReleaseRegistryBootstrap,
)


BOOTSTRAP = ReleaseRegistryBootstrapId("bootstrap-241")
PUBLIC_KEY = ReleaseSigningPublicKey(
    "SHA256:" + "A" * 43,
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFoundationBootstrapKey",
)
RESULT = BootstrappedReleaseRegistry(
    BOOTSTRAP,
    ReleaseRegistryLifecycleAuthorityId("lifecycle-241"),
    ReleaseSignerAuthorityId("signer-241"),
    ReleaseSigningKeyId("key-241"),
    ReleaseRegistrySetRevisionId("revision-241"),
    ReleasePolicyRevisionId("policy-241"),
)
T = TypeVar("T")


class Source(Generic[T]):
    def __init__(self, value: T | Exception) -> None:
        self.value = value
        self.calls = 0

    def __call__(self) -> T:
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'release-bootstrap.db'}")

    upgrade_to_head(str(database.url))
    try:
        yield database
    finally:
        database.dispose()


def _store(
    engine: Engine,
    lifecycle: Source | None = None,
    signer: Source | None = None,
    key: Source | None = None,
    revision: Source | None = None,
    policy: Source | None = None,
) -> DatabaseInitialReleaseRegistryBootstrap:
    return DatabaseInitialReleaseRegistryBootstrap(
        engine,
        generate_lifecycle_authority_id=lifecycle
        or Source(RESULT.lifecycle_authority_id),
        generate_signer_authority_id=signer or Source(RESULT.signer_authority_id),
        generate_key_id=key or Source(RESULT.key_id),
        generate_registry_revision_id=revision
        or Source(RESULT.registry_revision_id),
        generate_policy_revision_id=policy or Source(RESULT.policy_revision_id),
    )


def test_port_shape_accepts_only_stable_id_and_public_key() -> None:
    parameters = inspect.signature(InitialReleaseRegistryBootstrap.bootstrap).parameters
    assert list(parameters) == ["self", "bootstrap_id", "public_key"]
    assert "allow" not in parameters
    assert "role" not in parameters
    assert "authority_id" not in parameters


def test_bootstrap_creates_exact_initial_inactive_key_snapshot(engine: Engine) -> None:
    port: InitialReleaseRegistryBootstrap = _store(engine)

    assert port.bootstrap(BOOTSTRAP, PUBLIC_KEY) == RESULT
    with engine.connect() as connection:
        assert connection.execute(text(
            "SELECT revision.policy_status,signer.status,lifecycle.status,key.status "
            "FROM release_registry_current_set AS current "
            "JOIN release_registry_set_revisions AS revision "
            "ON revision.revision_id=current.revision_id "
            "JOIN release_registry_revision_signers AS signer "
            "ON signer.revision_id=current.revision_id "
            "JOIN release_registry_revision_lifecycle_authorities AS lifecycle "
            "ON lifecycle.revision_id=current.revision_id "
            "JOIN release_registry_revision_keys AS key "
            "ON key.revision_id=current.revision_id"
        )).one() == ("active", "active", "active", "inactive")
        assert connection.execute(text(
            "SELECT algorithm,namespace,fingerprint,public_key "
            "FROM release_signing_keys"
        )).one() == (
            "ssh-ed25519",
            "liquent-operations-release-v1",
            PUBLIC_KEY.fingerprint,
            PUBLIC_KEY.public_key,
        )
        assert connection.scalar(text(
            "SELECT count(*) FROM release_signing_decisions"
        )) == 0
        assert connection.scalar(text(
            "SELECT count(*) FROM release_registry_lifecycle_changes"
        )) == 0


def test_exact_retry_returns_committed_ids_without_generation(engine: Engine) -> None:
    assert _store(engine).bootstrap(BOOTSTRAP, PUBLIC_KEY) == RESULT
    sources = [Source(RuntimeError("must not draw")) for _ in range(5)]
    retry = _store(engine, *sources)

    assert retry.bootstrap(BOOTSTRAP, PUBLIC_KEY) == RESULT
    assert [source.calls for source in sources] == [0, 0, 0, 0, 0]


def test_same_bootstrap_id_with_other_key_is_detail_free_conflict(
    engine: Engine,
) -> None:
    assert _store(engine).bootstrap(BOOTSTRAP, PUBLIC_KEY) == RESULT
    other = ReleaseSigningPublicKey(
        "SHA256:" + "B" * 43,
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOtherBootstrapKey",
    )

    with pytest.raises(ReleaseRegistryBootstrapConflict) as raised:
        _store(engine).bootstrap(BOOTSTRAP, other)
    assert raised.value.args == ("release_registry_bootstrap_conflict",)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_other_bootstrap_id_after_history_is_neutral_and_draws_nothing(
    engine: Engine,
) -> None:
    assert _store(engine).bootstrap(BOOTSTRAP, PUBLIC_KEY) == RESULT
    sources = [Source(RuntimeError("must not draw")) for _ in range(5)]

    assert _store(engine, *sources).bootstrap(
        ReleaseRegistryBootstrapId("other-bootstrap"), PUBLIC_KEY
    ) is None
    assert [source.calls for source in sources] == [0, 0, 0, 0, 0]


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO release_signer_authorities VALUES (X'73')",
        "INSERT INTO release_registry_lifecycle_authorities VALUES (X'6c')",
        "INSERT INTO release_registry_set_revisions VALUES (X'72',X'70','active')",
    ],
)
def test_any_partial_history_permanently_closes_without_generation(
    engine: Engine, statement: str,
) -> None:
    with engine.begin() as connection:
        connection.execute(text(statement))
    sources = [Source(RuntimeError("must not draw")) for _ in range(5)]

    assert _store(engine, *sources).bootstrap(BOOTSTRAP, PUBLIC_KEY) is None
    assert [source.calls for source in sources] == [0, 0, 0, 0, 0]


@pytest.mark.parametrize("index", range(5))
def test_generator_failure_rolls_back_every_bootstrap_fact(
    engine: Engine, index: int,
) -> None:
    values = [
        RESULT.lifecycle_authority_id,
        RESULT.signer_authority_id,
        RESULT.key_id,
        RESULT.registry_revision_id,
        RESULT.policy_revision_id,
    ]
    sources = [Source(value) for value in values]
    sources[index] = Source(RuntimeError("generator"))

    with pytest.raises(ReleaseRegistryBootstrapUnavailable) as raised:
        _store(engine, *sources).bootstrap(BOOTSTRAP, PUBLIC_KEY)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT (SELECT count(*) FROM release_registry_bootstraps) + "
            "(SELECT count(*) FROM release_registry_set_revisions) + "
            "(SELECT count(*) FROM release_signing_keys)"
        )) == 0


def test_invalid_input_and_unmigrated_store_are_detail_free(
    engine: Engine, tmp_path: Path,
) -> None:
    with pytest.raises(ReleaseRegistryBootstrapUnavailable):
        _store(engine).bootstrap("not-an-id", PUBLIC_KEY)  # type: ignore[arg-type]
    unmigrated = build_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    store = _store(unmigrated)
    try:
        with pytest.raises(ReleaseRegistryBootstrapUnavailable) as raised:
            store.bootstrap(BOOTSTRAP, PUBLIC_KEY)
        assert raised.value.args == ("release_registry_bootstrap_unavailable",)
        assert raised.value.__cause__ is None
        assert raised.value.__context__ is None
        assert repr(store) == "DatabaseInitialReleaseRegistryBootstrap()"
    finally:
        unmigrated.dispose()
