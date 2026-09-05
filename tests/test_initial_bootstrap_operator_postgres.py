import json
from pathlib import Path

import pytest
from sqlalchemy import Engine

from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.operators.initial_bootstrap import (
    bootstrap_identity,
    bootstrap_oidc_trust_authority,
    main,
)

pytestmark = pytest.mark.postgres_integration


def _private(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def test_bootstrap_chain_and_exact_recovery_on_postgresql(
    postgres_engine: Engine,
) -> None:
    material = SecureIdentityAuthorityMaterialGenerator()

    identity = bootstrap_identity(postgres_engine, material)
    identity_retry = bootstrap_identity(postgres_engine, material)
    assert identity is not None and identity.recovered is False
    assert identity_retry is not None and identity_retry.recovered is True
    assert identity_retry.result == identity.result
    assert identity_retry.user_revision_id == identity.user_revision_id
    assert (
        identity_retry.workspace_revision_id
        == identity.workspace_revision_id
    )

    trust = bootstrap_oidc_trust_authority(
        postgres_engine, identity.result.user_id
    )
    trust_retry = bootstrap_oidc_trust_authority(
        postgres_engine, identity.result.user_id
    )
    assert trust is not None and trust.recovered is False
    assert trust_retry is not None and trust_retry.recovered is True
    assert trust_retry.result == trust.result


def test_cli_retry_preserves_four_field_result_on_postgresql(
    postgres_url: str, tmp_path: Path
) -> None:
    database = _private(tmp_path / "database-url", postgres_url)
    first = tmp_path / "first.json"
    assert main([
        "identity", "--database-url-file", str(database),
        "--result-file", str(first),
    ]) == 0
    first_value = json.loads(first.read_text(encoding="utf-8"))
    repeated = tmp_path / "repeated.json"
    assert main([
        "identity", "--database-url-file", str(database),
        "--result-file", str(repeated),
    ]) == 0

    assert set(first_value) == {
        "user_id", "workspace_id", "user_revision_id",
        "workspace_revision_id",
    }
    assert repeated.read_text(encoding="utf-8") == first.read_text(
        encoding="utf-8"
    )
    assert first.stat().st_mode & 0o777 == 0o600
    assert repeated.stat().st_mode & 0o777 == 0o600
