from pathlib import Path


def test_lifecycle_control_plane_is_absent_from_http_runtime() -> None:
    root = Path(__file__).resolve().parents[1]
    runtime = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "src/liquent_platform/transport/http/main.py",
            "src/liquent_platform/transport/http/app.py",
        )
    )
    for token in (
        "operators.user_lifecycle",
        "operators.workspace_lifecycle",
        "DatabaseAuthorizedUserLifecycleChanges",
        "DatabaseAuthorizedWorkspaceLifecycleChanges",
    ):
        assert token not in runtime


def test_operator_entry_points_are_separate_and_non_recovering() -> None:
    root = Path(__file__).resolve().parents[1]
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    user = (root / "src/liquent_platform/operators/user_lifecycle.py").read_text(
        encoding="utf-8"
    )
    workspace = (
        root / "src/liquent_platform/operators/workspace_lifecycle.py"
    ).read_text(encoding="utf-8")

    assert "liquent-user-lifecycle =" in project
    assert "liquent-workspace-lifecycle =" in project
    for source in (user, workspace):
        assert 'add_parser("recover")' not in source
        assert 'add_parser("bootstrap")' not in source
        assert "upgrade_to_head" not in source
    assert 'commands.add_parser("reactivate")' not in workspace


def test_lifecycle_mutations_have_no_delete_or_reassignment_path() -> None:
    root = Path(__file__).resolve().parents[1]
    sources = "\n".join(
        (root / path).read_text(encoding="utf-8").upper()
        for path in (
            "src/liquent_platform/persistence/user_lifecycle_changes.py",
            "src/liquent_platform/persistence/workspace_lifecycle_changes.py",
        )
    )
    assert "DELETE FROM IDENTITY_USERS" not in sources
    assert "DELETE FROM IDENTITY_WORKSPACES" not in sources
    assert "SET USER_ID=" not in sources
    assert "SET WORKSPACE_ID=" not in sources
