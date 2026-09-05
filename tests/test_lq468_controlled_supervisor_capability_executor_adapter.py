import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_capability_executor.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _methods() -> list[str]:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return [node.name for node in cls.body if isinstance(node, ast.FunctionDef)]


def test_adapter_has_two_profile_specific_execution_methods() -> None:
    methods = _methods()
    assert "execute_writer" in methods and "execute_recovery" in methods
    assert not {"execute", "run", "poll", "wait"} & set(methods)


def test_writer_delegates_once_with_prepared_binding() -> None:
    text = _text()
    assert text.count("self._writer.release_writer(") == 1
    assert "prepared.handle_id, prepared.claim_id, prepared.owner_id" in text
    assert "type(outcome) is not CompletedManifestHandoffWriterProcess" in text
    assert "ExecutedManifestHandoffWriterCapability(request, outcome)" in text


def test_recovery_delegates_once_with_prepared_binding() -> None:
    text = _text()
    assert text.count("self._recovery.release_recovery(") == 1
    assert text.count("prepared.handle_id, prepared.claim_id, prepared.owner_id") == 2
    assert "type(outcome) is not CompletedManifestHandoffRecoveryProcess" in text
    assert "ExecutedManifestHandoffRecoveryCapability(request, outcome)" in text


def test_running_none_conflict_and_wrong_type_are_not_accepted() -> None:
    text = _text()
    assert text.count("type(outcome) is not CompletedManifestHandoff") == 2
    assert "RunningManifestHandoff" not in text
    assert "return None" not in text
    assert "ManifestHandoffSupervisorConflict" not in text


def test_adapter_does_not_poll_inspect_terminate_or_retry() -> None:
    text = _text()
    for forbidden in ("inspect_writer", "inspect_recovery", "terminate_writer",
                      "terminate_recovery", "sleep", "retry"):
        assert forbidden not in text
    tree = ast.parse(text)
    assert not any(isinstance(node, (ast.For, ast.AsyncFor, ast.While)) for node in ast.walk(tree))


def test_errors_are_detail_free_and_repr_hides_dependencies() -> None:
    text = _text()
    assert 'return "ControlledManifestHandoffSupervisorCapabilityExecutor()"' in text
    assert text.count("raise ManifestHandoffRegistryUnavailable from None") == 2
    assert text.count("except ManifestHandoffRegistryUnavailable") == 2


def test_no_file_engine_authority_or_process_parameters() -> None:
    text = _text()
    for forbidden in ("SessionPrincipal", "Permission", "allow", "authorized", "docker",
                      "subprocess", "Popen", "socket", "open(", "Path", "command:", "timeout:"):
        assert forbidden not in text


def test_roadmap_records_lq468_and_next_async_outcome_contract() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-468 controlled supervisor capability executor adapter:" in roadmap
    assert "lq-468-controlled-supervisor-capability-executor-adapter.md" in roadmap
    assert "nächster Slice LQ-469" in roadmap
