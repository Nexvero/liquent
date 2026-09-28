import json
from pathlib import Path

from liquent_platform.operators.initial_bootstrap import main as bootstrap_main
from liquent_platform.operators.user_lifecycle import main as user_main
from liquent_platform.operators.workspace_lifecycle import main as workspace_main
from liquent_platform.persistence.migrate import upgrade_to_head


def _private(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return path


def test_identity_bootstrap_result_supplies_required_lifecycle_revisions(
    tmp_path: Path,
) -> None:
    url = f"sqlite:///{tmp_path / 'lq227.db'}"
    upgrade_to_head(url)
    database = _private(tmp_path / "database-url", url)
    result_path = tmp_path / "identity-result.json"

    assert bootstrap_main([
        "identity", "--database-url-file", str(database),
        "--result-file", str(result_path),
    ]) == 0

    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert set(result) == {
        "user_id", "workspace_id", "user_revision_id",
        "workspace_revision_id",
    }
    assert result["user_revision_id"]
    assert result["workspace_revision_id"]


def test_bootstrap_result_drives_both_regular_create_operators(
    tmp_path: Path,
) -> None:
    url = f"sqlite:///{tmp_path / 'integrated.db'}"
    upgrade_to_head(url)
    database = _private(tmp_path / "integrated-database-url", url)
    bootstrap_result_path = tmp_path / "bootstrap-result.json"
    assert bootstrap_main([
        "identity", "--database-url-file", str(database),
        "--result-file", str(bootstrap_result_path),
    ]) == 0
    bootstrap = json.loads(
        bootstrap_result_path.read_text(encoding="utf-8")
    )

    user_request = _private(tmp_path / "user-request.json", json.dumps({
        "actor_user_id": bootstrap["user_id"],
        "change_id": "lq229-integrated-user",
        "expected_revision": bootstrap["user_revision_id"],
    }))
    user_result_path = tmp_path / "user-result.json"
    assert user_main([
        "create", "--database-url-file", str(database), "--request",
        str(user_request), "--result-file", str(user_result_path),
    ]) == 0
    user = json.loads(user_result_path.read_text(encoding="utf-8"))

    workspace_request = _private(
        tmp_path / "workspace-request.json",
        json.dumps({
            "actor_user_id": bootstrap["user_id"],
            "change_id": "lq229-integrated-workspace",
            "initial_onboarding_manager_user_id": user["user_id"],
            "expected_revision": bootstrap["workspace_revision_id"],
        }),
    )
    workspace_result_path = tmp_path / "workspace-result.json"
    assert workspace_main([
        "create", "--database-url-file", str(database), "--request",
        str(workspace_request), "--result-file", str(workspace_result_path),
    ]) == 0
    workspace = json.loads(
        workspace_result_path.read_text(encoding="utf-8")
    )

    assert user["user_id"]
    assert workspace["workspace_id"]
    assert user_result_path.stat().st_mode & 0o777 == 0o600
    assert workspace_result_path.stat().st_mode & 0o777 == 0o600


def test_no_general_offline_operator_exposes_current_lifecycle_revisions() -> None:
    root = Path(__file__).resolve().parents[1]
    operators = root / "src/liquent_platform/operators"
    sources = {
        path.name: path.read_text(encoding="utf-8")
        for path in operators.glob("*.py")
    }

    assert "current-user-revision" not in "\n".join(sources.values())
    assert "current-workspace-revision" not in "\n".join(sources.values())
    assert 'commands.add_parser("inspect")' not in "\n".join(sources.values())
    assert 'commands.add_parser("status")' not in "\n".join(sources.values())

    bootstrap = sources["initial_bootstrap.py"]
    assert '"user_revision_id"' in bootstrap
    assert '"workspace_revision_id"' in bootstrap


def test_regular_operator_requests_require_unavailable_initial_revisions() -> None:
    root = Path(__file__).resolve().parents[1]
    user = (root / "src/liquent_platform/operators/user_lifecycle.py").read_text(
        encoding="utf-8"
    )
    workspace = (
        root / "src/liquent_platform/operators/workspace_lifecycle.py"
    ).read_text(encoding="utf-8")

    assert '"expected_revision"' in user
    assert '"expected_revision"' in workspace
    assert "UserLifecycleRevisionId" in user
    assert "WorkspaceLifecycleRevisionId" in workspace


def test_runtime_and_runbooks_do_not_supply_a_revision_shortcut() -> None:
    root = Path(__file__).resolve().parents[1]
    runtime = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "src/liquent_platform/transport/http/main.py",
            "src/liquent_platform/transport/http/app.py",
            "operations/runbooks/user-lifecycle.md",
            "operations/runbooks/workspace-lifecycle.md",
        )
    )

    assert "SELECT revision_id" not in runtime
    assert "user_lifecycle_current_revision" not in runtime
    assert "workspace_lifecycle_current_revision" not in runtime
    assert "direct SQL" not in runtime
