import ast
from pathlib import Path

ROOT = Path(__file__).parents[1]
SERVICE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_terminal_service.py"

def _text(): return SERVICE.read_text(encoding="utf-8")

def _methods():
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}

def test_profile_specific_completion_methods():
    assert {"complete_writer", "complete_recovery"} <= _methods()

def test_only_running_and_terminal_retry_are_supported():
    text = _text()
    assert "ManifestHandoffSupervisorJournalState.RUNNING" in text
    assert "ManifestHandoffSupervisorJournalState.TERMINAL_OBSERVED" in text
    assert "return inspect_terminal(command)" in text

def test_released_execution_is_reconstructed_without_execute():
    text = _text()
    for role in ("WRAPPER_READY", "RELEASE_TOKEN", "RELEASE_CONSUMED"):
        assert f"ManifestHandoffSupervisorControlArtifactRole.{role}" in text
    assert "inspect_outcome(inspection_type(execution))" in text
    assert ".execute_writer" not in text and ".execute_recovery" not in text

def test_running_outcome_returns_without_terminal_effect():
    text = _text()
    assert "if type(outcome) is running_observation_type:" in text
    assert "return result_type(journal, runtime, process)" in text

def test_envelope_facts_engine_end_reread_and_journal_are_ordered():
    text = _text()
    publish = text.index("self._wrapper.publish_terminal")
    record = text.index("self._artifacts.record_terminal_envelope")
    wait = text.index("self._engine.wait_terminal")
    reread = text.index("encoded = self._reader.read")
    journal = text.index("terminal = record_terminal")
    assert publish < record < wait < reread < journal

def test_terminal_outcome_and_observation_are_rechecked():
    text = _text()
    assert "document.correlation_id != gate.terminal_observation_id" in text
    assert "document.outcome != outcome.outcome" in text
    assert "ManifestHandoffSupervisorEngineState.EXITED" in text
    assert "ManifestHandoffSupervisorEngineState.DEAD" in text

def test_no_authority_terminate_cleanup_schema_or_wiring():
    text = _text()
    for forbidden in ("SessionPrincipal", "UserId", "WorkspaceId", "Permission",
            "allow", ".terminate(", "UPDATE ", "DELETE ", "create_app", "compose"):
        assert forbidden not in text

def test_roadmap_records_lq478_and_lq479():
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-478 persistent supervisor terminal orchestration:" in roadmap
    assert "lq-478-persistent-supervisor-terminal-orchestration.md" in roadmap
    assert "nächster Slice LQ-479" in roadmap
