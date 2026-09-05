import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
SERVICE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_prepare_service.py"


def _text() -> str:
    return SERVICE.read_text(encoding="utf-8")


def _methods() -> set[str]:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_service_exposes_only_both_profile_specific_prepare_operations() -> None:
    assert {"prepare_writer", "prepare_recovery"} <= _methods()
    text = _text()
    assert "def release_" not in text
    assert "def terminate_" not in text
    assert "def inspect_" not in text


def test_registration_and_launch_commit_precede_every_engine_operation() -> None:
    text = _text()
    register = text.index("journal = register(command.registration)")
    commit = text.index("journal = commit_launch(")
    create = text.index("runtime = self._create_and_bind")
    inspect = text.index("observation = self._engine.inspect")
    assert register < commit < create < inspect


def test_only_closed_prepare_restart_states_are_accepted() -> None:
    text = _text()
    assert "ManifestHandoffSupervisorJournalState.PREPARE_REGISTERED" in text
    assert "ManifestHandoffSupervisorJournalState.LAUNCH_COMMITTED" in text
    assert "ManifestHandoffSupervisorJournalState.PREPARED_GATED" in text
    assert "journal.state not in" in text


def test_runtime_is_resolved_before_create_and_fully_compared() -> None:
    text = _text()
    assert text.index("self._runtime.resolve_runtime") < text.index("self._engine.create")
    for field in ("handle_id", "creation_id", "control_directory_id", "image_digest"):
        assert f"runtime.{field}" in text


def test_runtime_and_gate_are_persisted_before_start() -> None:
    text = _text()
    bind_runtime = text.index("runtime = self._create_and_bind")
    bind_gate = text.index("gate = self._gates.bind_gate")
    start = text.index("started = self._engine.start")
    assert bind_runtime < bind_gate < start
    helper = text[text.index("def _create_and_bind"):]
    assert helper.index("self._engine.create") < helper.index("self._runtime.bind_runtime")


def test_start_requires_created_and_ready_requires_observed_running() -> None:
    text = _text()
    assert "observation.state is ManifestHandoffSupervisorEngineState.CREATED" in text
    assert "observation.state is not ManifestHandoffSupervisorEngineState.RUNNING" in text
    running = text.index("observation.state is not ManifestHandoffSupervisorEngineState.RUNNING")
    ready = text.index("ready = self._wrapper.publish_ready")
    assert running < ready


def test_ready_facts_are_recorded_before_gated_transition() -> None:
    text = _text()
    ready = text.index("ready = self._wrapper.publish_ready")
    record = text.index("recorded = self._artifacts.record_ready")
    gated = text.index("journal = record_gated(")
    assert ready < record < gated
    assert "ready.publication.facts" in text


def test_conflicts_are_detail_free_and_technical_failure_uses_existing_boundary() -> None:
    text = _text()
    assert "_CONFLICTS" in text
    assert "ManifestHandoffSupervisorServiceConflict()" in text
    assert "ManifestHandoffRegistryUnavailable" in text
    assert "class ManifestHandoffSupervisor" not in text


def test_no_authority_release_terminal_cleanup_or_wiring_is_added() -> None:
    text = _text()
    for forbidden in (
        "SessionPrincipal", "UserId", "WorkspaceId", "Permission", "allow",
        "CommitManifestHandoffSupervisorGateRelease", "TerminalEnvelope",
        "TerminateManifestHandoffSupervisor", "UPDATE ", "DELETE ", "docker",
        "subprocess", "create_app", "compose",
    ):
        assert forbidden not in text


def test_roadmap_records_lq475_and_next_release_slice() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-475 persistent supervisor prepare orchestration:" in roadmap
    assert "lq-475-persistent-supervisor-prepare-orchestration.md" in roadmap
    assert "nächster Slice LQ-476" in roadmap
