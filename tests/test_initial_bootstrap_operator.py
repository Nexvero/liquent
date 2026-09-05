import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.authority_material import (
    SecureIdentityAuthorityMaterialGenerator,
)
from liquent_platform.operators.initial_bootstrap import (
    InitialBootstrapOperatorUnavailable,
    bootstrap_identity,
    bootstrap_oidc_trust_authority,
    main,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


def _private_file(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    url = f"sqlite:///{tmp_path / 'bootstrap-operator.db'}"
    upgrade_to_head(url)
    database = build_engine(url)
    try:
        yield database
    finally:
        database.dispose()


def test_identity_bootstrap_and_exact_canonical_recovery(engine: Engine) -> None:
    created = bootstrap_identity(
        engine, SecureIdentityAuthorityMaterialGenerator()
    )
    recovered = bootstrap_identity(
        engine, SecureIdentityAuthorityMaterialGenerator()
    )

    assert created is not None and created.recovered is False
    assert recovered is not None and recovered.recovered is True
    assert recovered.result == created.result
    assert recovered.user_revision_id == created.user_revision_id
    assert recovered.workspace_revision_id == created.workspace_revision_id
    assert str(created.result.user_id) not in repr(created)
    assert created.user_revision_id.value not in repr(created)
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT revision_id FROM user_lifecycle_current_revision"
        )) == created.user_revision_id.value.encode()
        assert connection.scalar(text(
            "SELECT revision_id FROM workspace_lifecycle_current_revision"
        )) == created.workspace_revision_id.value.encode()


def test_noncanonical_existing_identity_inventory_stays_closed(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users (user_id,status) VALUES (x'75','active')"
        ))

    assert bootstrap_identity(
        engine, SecureIdentityAuthorityMaterialGenerator()
    ) is None


def test_trust_authority_bootstrap_recovers_only_the_same_active_target(
    engine: Engine,
) -> None:
    identity = bootstrap_identity(engine, SecureIdentityAuthorityMaterialGenerator())
    assert identity is not None
    user = identity.result.user_id

    created = bootstrap_oidc_trust_authority(engine, user)
    recovered = bootstrap_oidc_trust_authority(engine, user)
    other = bootstrap_oidc_trust_authority(engine, UserId("other-user"))

    assert created is not None and created.recovered is False
    assert recovered is not None and recovered.recovered is True
    assert other is None


def test_cli_bootstraps_both_steps_and_writes_owner_only_results(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = _private_file(tmp_path / "database-url", str(engine.url))
    identity_result = tmp_path / "identity-result.json"

    assert main([
        "identity", "--database-url-file", str(database_url),
        "--result-file", str(identity_result),
    ]) == 0
    identity = json.loads(identity_result.read_text(encoding="utf-8"))
    assert set(identity) == {
        "user_id", "workspace_id", "user_revision_id",
        "workspace_revision_id",
    }
    assert identity_result.stat().st_mode & 0o777 == 0o600
    user_file = _private_file(tmp_path / "user-id", identity["user_id"] + "\n")
    trust_result = tmp_path / "trust-result.json"
    assert main([
        "oidc-trust-authority", "--database-url-file", str(database_url),
        "--user-id-file", str(user_file), "--result-file", str(trust_result),
    ]) == 0

    output = capsys.readouterr()
    assert output.err == ""
    assert output.out.splitlines() == [
        '{"outcome":"bootstrapped"}', '{"outcome":"bootstrapped"}'
    ]
    assert json.loads(trust_result.read_text(encoding="utf-8")) == {
        "user_id": identity["user_id"]
    }


def test_cli_recovers_after_result_file_was_not_preserved(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = _private_file(tmp_path / "database-url", str(engine.url))
    first = tmp_path / "first.json"
    assert main([
        "identity", "--database-url-file", str(database_url),
        "--result-file", str(first),
    ]) == 0
    expected = first.read_text(encoding="utf-8")
    first.unlink()
    recovered = tmp_path / "recovered.json"

    assert main([
        "identity", "--database-url-file", str(database_url),
        "--result-file", str(recovered),
    ]) == 0

    assert recovered.read_text(encoding="utf-8") == expected
    assert capsys.readouterr().out.splitlines()[-1] == '{"outcome":"recovered"}'


def test_existing_result_file_and_unsafe_inputs_fail_without_overwrite(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = _private_file(tmp_path / "database-url", str(engine.url))
    result = _private_file(tmp_path / "result.json", "KEEP")

    with pytest.raises(SystemExit) as raised:
        main([
            "identity", "--database-url-file", str(database_url),
            "--result-file", str(result),
        ])

    assert raised.value.code == 2
    assert result.read_text(encoding="utf-8") == "KEEP"
    assert capsys.readouterr().err == (
        '{"error":"initial_bootstrap_operator_unavailable"}\n'
    )


def test_operator_does_not_migrate_an_empty_database(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    url = f"sqlite:///{tmp_path / 'empty.db'}"
    database_url = _private_file(tmp_path / "database-url", url)

    with pytest.raises(SystemExit) as raised:
        main([
            "identity", "--database-url-file", str(database_url),
            "--result-file", str(tmp_path / "result.json"),
        ])

    assert raised.value.code == 2
    assert capsys.readouterr().err == (
        '{"error":"initial_bootstrap_operator_unavailable"}\n'
    )


def test_committed_bootstrap_is_recoverable_after_result_write_failure(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = _private_file(tmp_path / "database-url", str(engine.url))
    unsafe = tmp_path / "unsafe"
    unsafe.mkdir(mode=0o755)

    with pytest.raises(SystemExit):
        main([
            "identity", "--database-url-file", str(database_url),
            "--result-file", str(unsafe / "result.json"),
        ])
    recovered = tmp_path / "recovered.json"
    assert main([
        "identity", "--database-url-file", str(database_url),
        "--result-file", str(recovered),
    ]) == 0

    assert json.loads(recovered.read_text(encoding="utf-8")).keys() == {
        "user_id", "workspace_id", "user_revision_id",
        "workspace_revision_id",
    }
    output = capsys.readouterr()
    assert '{"outcome":"recovered"}' in output.out


def test_entry_point_is_packaged_separately() -> None:
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert (
        'liquent-initial-bootstrap = '
        '"liquent_platform.operators.initial_bootstrap:main"'
    ) in pyproject
