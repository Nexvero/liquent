import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from liquent_platform.operators.membership_management import (
    MembershipManagementOperatorInputRejected,
    load_bootstrap_request,
    load_change_request,
    main,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.migrate import upgrade_to_head


def _private(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def _bootstrap_request(**overrides: Any) -> dict[str, Any]:
    value = {"user_id": "manager-210", "workspace_id": "workspace-210"}
    value.update(overrides)
    return value


def _change_request(**overrides: Any) -> dict[str, Any]:
    value = {
        "actor_user_id": "manager-210",
        "change_id": "change-210",
        "target_user_id": "member-210",
        "workspace_id": "workspace-210",
        "expected_revision": None,
        "status": "active",
        "permissions": ["research:read", "research:write"],
    }
    value.update(overrides)
    return value


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    url = f"sqlite:///{tmp_path / 'operator.db'}"
    upgrade_to_head(url)
    database = build_engine(url)
    with database.begin() as connection:
        connection.execute(text(
            "INSERT INTO identity_users VALUES"
            " (x'6d616e616765722d323130','active'),"
            " (x'6d656d6265722d323130','active')"
        ))
        connection.execute(text(
            "INSERT INTO identity_workspaces VALUES"
            " (x'776f726b73706163652d323130','active')"
        ))
    try:
        yield database
    finally:
        database.dispose()


def test_exact_private_requests_are_parsed_without_normalization(
    tmp_path: Path,
) -> None:
    bootstrap_path = _private(
        tmp_path / "bootstrap.json", json.dumps(_bootstrap_request())
    )
    change_path = _private(
        tmp_path / "change.json", json.dumps(_change_request())
    )

    bootstrap = load_bootstrap_request(bootstrap_path)
    change = load_change_request(change_path)

    assert bootstrap.user_id == "manager-210"
    assert change.change_id.value == "change-210"
    assert {permission.value for permission in change.permissions} == {
        "research:read", "research:write"
    }
    assert "manager-210" not in repr(bootstrap) + repr(change)


@pytest.mark.parametrize(
    "payload",
    [
        {**_change_request(), "extra": True},
        _change_request(change_id=""),
        _change_request(status="unknown"),
        _change_request(permissions=["research:read", "research:read"]),
        _change_request(status="inactive", permissions=["research:read"]),
        _change_request(permissions=["admin"]),
    ],
)
def test_non_exact_change_request_is_rejected_detail_free(
    tmp_path: Path, payload: dict[str, Any]
) -> None:
    path = _private(tmp_path / "request.json", json.dumps(payload))

    with pytest.raises(MembershipManagementOperatorInputRejected) as raised:
        load_change_request(path)

    assert raised.value.args == ("membership_management_operator_input_rejected",)
    assert raised.value.__cause__ is None


def test_new_change_id_emits_one_opaque_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["new-change-id"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert len(output.out.strip()) >= 43


def test_cli_bootstraps_authority_and_applies_membership(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    bootstrap_request = _private(
        tmp_path / "bootstrap.json", json.dumps(_bootstrap_request())
    )
    bootstrap_result = tmp_path / "bootstrap-result.json"
    assert main([
        "bootstrap-authority", "--database-url-file", str(database),
        "--request", str(bootstrap_request), "--result-file",
        str(bootstrap_result),
    ]) == 0
    change_request = _private(
        tmp_path / "change.json", json.dumps(_change_request())
    )
    change_result = tmp_path / "change-result.json"
    assert main([
        "apply", "--database-url-file", str(database), "--request",
        str(change_request), "--result-file", str(change_result),
    ]) == 0

    output = capsys.readouterr()
    assert output.err == ""
    assert output.out.splitlines() == [
        '{"outcome":"bootstrapped"}', '{"outcome":"applied"}'
    ]
    result = json.loads(change_result.read_text(encoding="utf-8"))
    assert result["change_id"] == "change-210"
    assert result["revision_id"]
    assert change_result.stat().st_mode & 0o777 == 0o600


def test_exact_retry_after_authority_revocation_returns_same_revision(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    bootstrap = _private(
        tmp_path / "bootstrap.json", json.dumps(_bootstrap_request())
    )
    assert main([
        "bootstrap-authority", "--database-url-file", str(database),
        "--request", str(bootstrap), "--result-file",
        str(tmp_path / "bootstrap-result.json"),
    ]) == 0
    request = _private(tmp_path / "change.json", json.dumps(_change_request()))
    first = tmp_path / "first.json"
    assert main([
        "apply", "--database-url-file", str(database), "--request",
        str(request), "--result-file", str(first),
    ]) == 0
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE workspace_membership_management_authorities"
            " SET status='inactive'"
        ))
    repeated = tmp_path / "repeated.json"
    assert main([
        "apply", "--database-url-file", str(database), "--request",
        str(request), "--result-file", str(repeated),
    ]) == 0

    assert repeated.read_text(encoding="utf-8") == first.read_text(encoding="utf-8")
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_membership_revisions"
        )) == 1
    assert capsys.readouterr().err == ""


def test_bootstrap_exact_recovery_and_different_target_rejection(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    request = _private(
        tmp_path / "bootstrap.json", json.dumps(_bootstrap_request())
    )
    assert main([
        "bootstrap-authority", "--database-url-file", str(database),
        "--request", str(request), "--result-file", str(tmp_path / "one.json"),
    ]) == 0
    assert main([
        "bootstrap-authority", "--database-url-file", str(database),
        "--request", str(request), "--result-file", str(tmp_path / "two.json"),
    ]) == 0
    other = _private(
        tmp_path / "other.json",
        json.dumps(_bootstrap_request(user_id="member-210")),
    )
    assert main([
        "bootstrap-authority", "--database-url-file", str(database),
        "--request", str(other), "--result-file", str(tmp_path / "three.json"),
    ]) == 5

    assert capsys.readouterr().out.splitlines() == [
        '{"outcome":"bootstrapped"}', '{"outcome":"recovered"}',
        '{"outcome":"rejected"}',
    ]
    assert not (tmp_path / "three.json").exists()


def test_existing_result_is_not_overwritten(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    request = _private(
        tmp_path / "bootstrap.json", json.dumps(_bootstrap_request())
    )
    result = _private(tmp_path / "result.json", "KEEP")

    with pytest.raises(SystemExit) as raised:
        main([
            "bootstrap-authority", "--database-url-file", str(database),
            "--request", str(request), "--result-file", str(result),
        ])

    assert raised.value.code == 4
    assert result.read_text(encoding="utf-8") == "KEEP"
    assert "manager-210" not in capsys.readouterr().err


def test_console_entry_point_is_packaged() -> None:
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert (
        'liquent-membership-management = '
        '"liquent_platform.operators.membership_management:main"'
    ) in pyproject
