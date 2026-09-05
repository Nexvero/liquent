import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
SERVICE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_inspect_service.py"


def _text() -> str:
    return SERVICE.read_text(encoding="utf-8")


def _methods() -> set[str]:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_service_exposes_profile_specific_inspect() -> None:
    assert {"inspect_writer", "inspect_recovery"} <= _methods()


def test_only_three_persistently_visible_states_are_reconstructed() -> None:
    text = _text()
    for state in ("PREPARED_GATED", "RUNNING", "TERMINAL_OBSERVED"):
        assert f"ManifestHandoffSupervisorJournalState.{state}" in text
    for state in ("PREPARE_REGISTERED", "LAUNCH_COMMITTED", "RELEASE_COMMITTED",
                  "TERMINATION_REQUESTED"):
        assert f"ManifestHandoffSupervisorJournalState.{state}" not in text


def test_unknown_journal_is_the_only_neutral_none() -> None:
    text = _text()
    assert "if journal is None:\n                return None" in text
    assert text.count("return None") == 1


def test_runtime_gate_ready_and_physical_document_are_required() -> None:
    text = _text()
    assert "self._runtime.resolve_runtime" in text
    assert "self._gates.resolve_gate" in text
    assert "ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY" in text
    assert "self._reader.read" in text and "self._codec.decode" in text


def test_running_requires_token_consumed_and_direct_engine_running() -> None:
    text = _text()
    assert "ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN" in text
    assert "ManifestHandoffSupervisorControlArtifactRole.RELEASE_CONSUMED" in text
    assert "self._require_released(journal, gate)" in text
    assert "ManifestHandoffSupervisorEngineState.RUNNING" in text


def test_terminal_requires_envelope_outcome_and_engine_terminal() -> None:
    text = _text()
    assert "ManifestHandoffSupervisorControlArtifactRole.TERMINAL_ENVELOPE" in text
    assert "document.outcome != journal.result" in text
    assert "journal.terminal_observation_id != gate.terminal_observation_id" in text
    assert "if journal.release_id is not None:" in text
    assert "ManifestHandoffSupervisorEngineState.EXITED" in text
    assert "ManifestHandoffSupervisorEngineState.DEAD" in text


def test_inspect_has_no_mutating_boundary_calls() -> None:
    text = _text()
    for forbidden in (".register_", ".commit_", ".record_", ".bind_", ".create(",
            ".start(", ".publish(", ".execute_", ".wait_", ".terminate("):
        assert forbidden not in text


def test_no_authority_cleanup_schema_or_wiring() -> None:
    text = _text()
    for forbidden in ("SessionPrincipal", "UserId", "WorkspaceId", "Permission",
            "allow", "UPDATE ", "DELETE ", "create_app", "compose"):
        assert forbidden not in text


def test_roadmap_records_lq477_and_next_terminal_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-477 read-only persistent supervisor inspect orchestration:" in roadmap
    assert "lq-477-read-only-persistent-supervisor-inspect-orchestration.md" in roadmap
    assert "nächster Slice LQ-478" in roadmap
