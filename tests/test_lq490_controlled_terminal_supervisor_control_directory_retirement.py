import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
LIFECYCLE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_control_directory_retirement.py"


def _text() -> str:
    return LIFECYCLE.read_text(encoding="utf-8")


def test_lifecycle_exposes_only_retire() -> None:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    methods = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}
    assert "retire" in methods
    assert not {"remove", "delete", "cleanup", "rotate", "activate"} & methods


def test_current_directory_is_resolved_before_any_journal_read() -> None:
    text = _text()
    resolve = text.index("self._registry.resolve_control_directory(directory_id)")
    writer = text.index("self._journal.inspect_writer_journal(lifecycle.handle_id)")
    recovery = text.index("self._journal.inspect_recovery_journal(lifecycle.handle_id)")
    assert resolve < writer < recovery


def test_unknown_reserved_and_retired_are_closed_before_journal() -> None:
    text = _text()
    section = text[text.index("lifecycle ="):text.index("writer =")]
    assert "if lifecycle is None:" in section and "return None" in section
    assert "type(lifecycle) is RetiredManifestHandoffSupervisorControlDirectory" in section
    assert "type(lifecycle) is ReservedManifestHandoffSupervisorControlDirectory" in section
    assert "ManifestHandoffSupervisorControlDirectoryConflict()" in section


def test_exactly_one_closed_journal_view_is_required() -> None:
    text = _text()
    assert "views = [view for view in (writer, recovery) if view is not None]" in text
    assert "if len(views) != 1:" in text
    assert "ManifestHandoffWriterJournalView" in text
    assert "ManifestHandoffRecoveryJournalView" in text


def test_terminal_state_handle_identity_and_result_precede_retire() -> None:
    text = _text()
    retire = text.index("self._registry.retire_control_directory(")
    for evidence in (
        "terminal.registration.handle_id != lifecycle.handle_id",
        "ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED",
        "terminal.terminal_observation_id is None",
        "terminal.result.handle_id != lifecycle.handle_id",
    ):
        assert text.index(evidence) < retire


def test_retire_uses_full_active_and_none_after_effect_is_technical() -> None:
    text = _text()
    assert "RetireManifestHandoffSupervisorControlDirectory(lifecycle)" in text
    assert "if retired is None" in text
    assert "type(retired) is not RetiredManifestHandoffSupervisorControlDirectory" in text
    assert "if retired.active != lifecycle:" in text


def test_existing_technical_boundary_and_no_file_cleanup_authority_or_wiring() -> None:
    text = _text()
    assert "ManifestHandoffRegistryUnavailable" in text
    for forbidden in (
        "SessionPrincipal", "UserId", "WorkspaceId", "Permission", "allow:",
        "Path", "os.", "unlink", "rmdir", "sqlalchemy", "create_app", "compose_",
    ):
        assert forbidden not in text


def test_roadmap_records_lq490_and_lq491() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-490 controlled terminal supervisor control-directory retirement:" in roadmap
    assert "lq-490-controlled-terminal-supervisor-control-directory-retirement.md" in roadmap
    assert "nächster Slice LQ-491" in roadmap
