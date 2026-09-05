import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_capability_outcome.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _class() -> ast.ClassDef:
    return next(node for node in ast.parse(_text()).body if isinstance(node, ast.ClassDef))


def test_constructor_has_bounded_constructive_wait_policy() -> None:
    text = _text()
    assert "not 1 <= maximum_observations <= 10_000" in text
    assert "self._maximum = maximum_observations" in text
    assert "self._pause = pause" in text


def test_writer_inspect_uses_prepared_binding_once() -> None:
    text = _text()
    assert text.count("self._writer.inspect_writer(") == 1
    assert "prepared.handle_id, prepared.claim_id, prepared.owner_id" in text
    assert "RunningManifestHandoffWriterCapability(request, state)" in text
    assert "ExecutedManifestHandoffWriterCapability(request.execution, state)" in text


def test_recovery_inspect_uses_prepared_binding_once() -> None:
    text = _text()
    assert text.count("self._recovery.inspect_recovery(") == 1
    assert text.count("prepared.handle_id, prepared.claim_id, prepared.owner_id") == 2
    assert "RunningManifestHandoffRecoveryCapability(request, state)" in text
    assert "ExecutedManifestHandoffRecoveryCapability(request.execution, state)" in text


def test_only_exact_running_or_completed_types_are_accepted() -> None:
    text = _text()
    for value in ("RunningManifestHandoffWriterProcess", "CompletedManifestHandoffWriterProcess",
                  "RunningManifestHandoffRecoveryProcess", "CompletedManifestHandoffRecoveryProcess"):
        assert f"type(state) is {value}" in text
    assert text.count("raise ManifestHandoffRegistryUnavailable") >= 7
    assert "return None" not in text


def test_wait_loops_are_bounded_and_terminal_only() -> None:
    text = _text()
    assert text.count("for index in range(self._maximum):") == 2
    assert "type(observed) is ExecutedManifestHandoffWriterCapability" in text
    assert "type(observed) is ExecutedManifestHandoffRecoveryCapability" in text
    assert text.count("if index + 1 < self._maximum:") == 2
    assert text.count("self._safe_pause()") == 2


def test_no_release_start_terminate_or_second_process_effect() -> None:
    text = _text()
    for forbidden in ("release_writer", "release_recovery", "start_writer", "start_recovery",
                      "terminate_writer", "terminate_recovery", "execute_writer", "execute_recovery"):
        assert forbidden not in text


def test_pause_is_detail_free_and_must_return_none() -> None:
    text = _text()
    assert "if self._pause() is not None" in text
    assert "raise ManifestHandoffRegistryUnavailable from None" in text
    assert 'return "ControlledManifestHandoffSupervisorCapabilityOutcome()"' in text


def test_no_engine_file_authority_or_request_timing_parameters() -> None:
    text = _text()
    for forbidden in ("SessionPrincipal", "Permission", "allow", "authorized", "docker",
                      "subprocess", "Popen", "socket", "open(", "Path", "timeout:", "clock:"):
        assert forbidden not in text


def test_roadmap_records_lq470_and_next_service_contract() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-470 controlled capability outcome inspect and bounded wait:" in roadmap
    assert "lq-470-controlled-capability-outcome-inspect-and-bounded-wait.md" in roadmap
    assert "nächster Slice LQ-471" in roadmap
