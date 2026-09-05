import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.lifecycle import (
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.operators.user_lifecycle import (
    UserLifecycleOperatorInputRejected,
    load_create_request as load_user_create,
    load_status_request as load_user_status,
    main as user_main,
)
from liquent_platform.operators.workspace_lifecycle import (
    WorkspaceLifecycleOperatorInputRejected,
    load_create_request as load_workspace_create,
    load_deactivate_request as load_workspace_deactivate,
    main as workspace_main,
)
from liquent_platform.persistence.database import build_engine
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)
from liquent_platform.persistence.migrate import upgrade_to_head

ACTOR = UserId("lifecycle-operator-actor")
INITIAL_WORKSPACE = WorkspaceId("lifecycle-operator-initial-workspace")
USER_REVISION = UserLifecycleRevisionId("lifecycle-operator-users")
WORKSPACE_REVISION = WorkspaceLifecycleRevisionId(
    "lifecycle-operator-workspaces"
)


def _private(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def _user_create(**overrides: Any) -> dict[str, Any]:
    value = {
        "actor_user_id": str(ACTOR),
        "change_id": "create-user-change",
        "expected_revision": USER_REVISION.value,
    }
    value.update(overrides)
    return value


def _user_status(revision: str, **overrides: Any) -> dict[str, Any]:
    value = {
        "actor_user_id": str(ACTOR),
        "change_id": "user-status-change",
        "target_user_id": "created-user",
        "expected_revision": revision,
    }
    value.update(overrides)
    return value


def _workspace_create(**overrides: Any) -> dict[str, Any]:
    value = {
        "actor_user_id": str(ACTOR),
        "change_id": "create-workspace-change",
        "initial_onboarding_manager_user_id": str(ACTOR),
        "expected_revision": WORKSPACE_REVISION.value,
    }
    value.update(overrides)
    return value


def _workspace_deactivate(revision: str, **overrides: Any) -> dict[str, Any]:
    value = {
        "actor_user_id": str(ACTOR),
        "change_id": "deactivate-workspace-change",
        "target_workspace_id": "created-workspace",
        "expected_revision": revision,
    }
    value.update(overrides)
    return value


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    database = build_engine(f"sqlite:///{tmp_path / 'lifecycle-operators.db'}")
    upgrade_to_head(str(database.url))
    assert DatabaseInitialIdentityAuthorityBootstrap(
        database,
        generate_user_id=lambda: ACTOR,
        generate_workspace_id=lambda: INITIAL_WORKSPACE,
        generate_user_revision_id=lambda: USER_REVISION,
        generate_workspace_revision_id=lambda: WORKSPACE_REVISION,
    ).bootstrap() is not None
    try:
        yield database
    finally:
        database.dispose()


def test_exact_private_requests_parse_without_identifier_repr(
    tmp_path: Path,
) -> None:
    requests = [
        load_user_create(_private(
            tmp_path / "user-create.json", json.dumps(_user_create())
        )),
        load_user_status(_private(
            tmp_path / "user-status.json",
            json.dumps(_user_status("next-user-revision")),
        )),
        load_workspace_create(_private(
            tmp_path / "workspace-create.json",
            json.dumps(_workspace_create()),
        )),
        load_workspace_deactivate(_private(
            tmp_path / "workspace-deactivate.json",
            json.dumps(_workspace_deactivate("next-workspace-revision")),
        )),
    ]
    assert "lifecycle-operator-actor" not in "".join(map(repr, requests))


@pytest.mark.parametrize(
    ("loader", "payload", "failure"),
    [
        (load_user_create, _user_create(target_user_id="caller-choice"),
         UserLifecycleOperatorInputRejected),
        (load_user_create, _user_create(allow=True),
         UserLifecycleOperatorInputRejected),
        (load_user_status, _user_status("revision", intent="reactivate"),
         UserLifecycleOperatorInputRejected),
        (load_workspace_create,
         _workspace_create(target_workspace_id="caller-choice"),
         WorkspaceLifecycleOperatorInputRejected),
        (load_workspace_create, _workspace_create(role="admin"),
         WorkspaceLifecycleOperatorInputRejected),
        (load_workspace_deactivate,
         _workspace_deactivate("revision", status="inactive"),
         WorkspaceLifecycleOperatorInputRejected),
    ],
)
def test_caller_controlled_ids_decisions_and_roles_are_rejected(
    tmp_path: Path, loader, payload: dict[str, Any], failure
) -> None:
    with pytest.raises(failure) as raised:
        loader(_private(tmp_path / "bad.json", json.dumps(payload)))
    assert raised.value.__cause__ is None


@pytest.mark.parametrize("main", [user_main, workspace_main])
def test_new_change_id_emits_one_opaque_value(main, capsys) -> None:
    assert main(["new-change-id"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert len(output.out.strip()) >= 43
    assert "{" not in output.out


def test_user_cli_creates_and_exactly_retries_after_revocation(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    request = _private(
        tmp_path / "request.json", json.dumps(_user_create())
    )
    first = tmp_path / "first-result.json"
    command = [
        "create", "--database-url-file", str(database),
        "--request", str(request), "--result-file",
    ]
    assert user_main([*command, str(first)]) == 0
    with engine.begin() as connection:
        connection.execute(text(
            "UPDATE user_lifecycle_management_authorities SET status='inactive'"
        ))
    repeated = tmp_path / "repeated-result.json"
    assert user_main([*command, str(repeated)]) == 0

    result = json.loads(first.read_text(encoding="utf-8"))
    assert set(result) == {"change_id", "revision_id", "user_id"}
    assert first.read_text(encoding="utf-8") == repeated.read_text(
        encoding="utf-8"
    )
    assert first.stat().st_mode & 0o777 == 0o600
    assert capsys.readouterr().out.splitlines() == [
        '{"outcome":"applied"}', '{"outcome":"applied"}'
    ]


def test_workspace_cli_creates_only_workspace_and_onboarding_manager(
    engine: Engine, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _private(tmp_path / "database-url", str(engine.url))
    request = _private(
        tmp_path / "request.json", json.dumps(_workspace_create())
    )
    result_path = tmp_path / "result.json"
    assert workspace_main([
        "create", "--database-url-file", str(database), "--request",
        str(request), "--result-file", str(result_path),
    ]) == 0
    result = json.loads(result_path.read_text(encoding="utf-8"))
    with engine.connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_memberships"
        )) == 0
        assert connection.execute(text(
            "SELECT user_id,status FROM workspace_onboarding_management"
            " WHERE workspace_id=:workspace"
        ), {"workspace": result["workspace_id"].encode()}).one() == (
            ACTOR.encode(), "active"
        )
    assert set(result) == {"change_id", "revision_id", "workspace_id"}
    assert result_path.stat().st_mode & 0o777 == 0o600
    assert capsys.readouterr().out == '{"outcome":"applied"}\n'


@pytest.mark.parametrize(
    ("main", "command", "request_value"),
    [
        (user_main, "create", _user_create()),
        (workspace_main, "create", _workspace_create()),
    ],
)
def test_operator_does_not_migrate_empty_database(
    main, command: str, request_value: dict[str, Any], tmp_path: Path, capsys
) -> None:
    database = _private(
        tmp_path / "database-url", f"sqlite:///{tmp_path / 'empty.db'}"
    )
    request = _private(tmp_path / "request.json", json.dumps(request_value))
    with pytest.raises(SystemExit) as raised:
        main([
            command, "--database-url-file", str(database), "--request",
            str(request), "--result-file", str(tmp_path / "result.json"),
        ])
    assert raised.value.code == 4
    assert "unavailable" in capsys.readouterr().err
