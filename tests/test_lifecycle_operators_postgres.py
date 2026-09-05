import json
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from liquent_platform.identity.access import UserId
from liquent_platform.identity.lifecycle import (
    UserLifecycleRevisionId,
    WorkspaceLifecycleRevisionId,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.operators.user_lifecycle import main as user_main
from liquent_platform.operators.workspace_lifecycle import main as workspace_main
from liquent_platform.persistence.identity_bootstrap import (
    DatabaseInitialIdentityAuthorityBootstrap,
)

pytestmark = pytest.mark.postgres_integration


def _private(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def test_operator_chain_creates_user_then_workspace_on_postgresql(
    postgres_engine: Engine, postgres_url: str, tmp_path: Path
) -> None:
    actor = UserId("lq226-postgres-actor")
    user_revision = UserLifecycleRevisionId("lq226-initial-users")
    workspace_revision = WorkspaceLifecycleRevisionId(
        "lq226-initial-workspaces"
    )
    assert DatabaseInitialIdentityAuthorityBootstrap(
        postgres_engine,
        generate_user_id=lambda: actor,
        generate_workspace_id=lambda: WorkspaceId("lq226-initial-workspace"),
        generate_user_revision_id=lambda: user_revision,
        generate_workspace_revision_id=lambda: workspace_revision,
    ).bootstrap() is not None
    database = _private(tmp_path / "database-url", postgres_url)

    user_request = _private(tmp_path / "user-request.json", json.dumps({
        "actor_user_id": str(actor),
        "change_id": "lq226-create-user",
        "expected_revision": user_revision.value,
    }))
    user_result_path = tmp_path / "user-result.json"
    assert user_main([
        "create", "--database-url-file", str(database), "--request",
        str(user_request), "--result-file", str(user_result_path),
    ]) == 0
    user_result = json.loads(user_result_path.read_text(encoding="utf-8"))

    workspace_request = _private(
        tmp_path / "workspace-request.json",
        json.dumps({
            "actor_user_id": str(actor),
            "change_id": "lq226-create-workspace",
            "initial_onboarding_manager_user_id": user_result["user_id"],
            "expected_revision": workspace_revision.value,
        }),
    )
    workspace_result_path = tmp_path / "workspace-result.json"
    assert workspace_main([
        "create", "--database-url-file", str(database), "--request",
        str(workspace_request), "--result-file", str(workspace_result_path),
    ]) == 0
    workspace_result = json.loads(
        workspace_result_path.read_text(encoding="utf-8")
    )

    with postgres_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT status FROM identity_users WHERE user_id=:user"
        ), {"user": user_result["user_id"].encode()}).scalar_one() == "active"
        assert connection.execute(text(
            "SELECT status FROM identity_workspaces WHERE workspace_id=:workspace"
        ), {
            "workspace": workspace_result["workspace_id"].encode()
        }).scalar_one() == "active"
        assert connection.execute(text(
            "SELECT user_id,status FROM workspace_onboarding_management"
            " WHERE workspace_id=:workspace"
        ), {
            "workspace": workspace_result["workspace_id"].encode()
        }).one() == (user_result["user_id"].encode(), "active")
        assert connection.scalar(text(
            "SELECT count(*) FROM workspace_memberships"
        )) == 0

    assert user_result_path.stat().st_mode & 0o777 == 0o600
    assert workspace_result_path.stat().st_mode & 0o777 == 0o600
