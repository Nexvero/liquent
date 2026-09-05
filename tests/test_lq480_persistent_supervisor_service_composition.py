import ast
from pathlib import Path

ROOT=Path(__file__).parents[1]
SERVICE=ROOT/"src/liquent_platform/application/manifest_handoff_supervisor_service.py"
def _text(): return SERVICE.read_text(encoding="utf-8")
def _public_methods():
    cls=next(n for n in ast.parse(_text()).body if isinstance(n,ast.ClassDef))
    return [n.name for n in cls.body if isinstance(n,ast.FunctionDef) and not n.name.startswith("_")]

def test_facade_exposes_exactly_eight_profile_methods():
    assert set(_public_methods()) == {
        "prepare_writer","release_writer","terminate_writer","inspect_writer",
        "prepare_recovery","release_recovery","terminate_recovery","inspect_recovery"}

def test_each_operation_delegates_to_matching_profile():
    text=_text()
    for operation in ("prepare","release","terminate","inspect"):
        for profile in ("writer","recovery"):
            assert f"self._{operation}.{operation}_{profile}" in text

def test_release_completion_uses_same_handle_only_after_running():
    text=_text()
    assert "result.journal.state is not ManifestHandoffSupervisorJournalState.RUNNING" in text
    assert "InspectManifestHandoffSupervisorService(command.handle_id)" in text
    assert "self._terminal.complete_writer" in text
    assert "self._terminal.complete_recovery" in text

def test_none_and_conflict_skip_completion():
    text=_text()
    assert "if result is None or type(result) is ManifestHandoffSupervisorServiceConflict:" in text
    assert "return result" in text

def test_inspect_does_not_invoke_completion():
    tree=ast.parse(_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
    for name in ("inspect_writer","inspect_recovery"):
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
        assert "_terminal" not in ast.unparse(method)

def test_no_low_level_authority_schema_or_wiring():
    text=_text()
    for forbidden in ("SessionPrincipal","UserId","WorkspaceId","Permission","allow",
            "sqlalchemy","Docker","Path","open(","subprocess","create_app","compose"):
        assert forbidden not in text

def test_roadmap_records_lq480_and_lq481():
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-480 persistent supervisor service composition:" in roadmap
    assert "lq-480-persistent-supervisor-service-composition.md" in roadmap
    assert "nächster Slice LQ-481" in roadmap
