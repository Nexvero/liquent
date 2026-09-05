import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_service.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"
DOC = ROOT / "docs/lq-472-persistent-supervisor-service-commands-results-and-ports.md"


def _classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _methods(node: ast.ClassDef) -> list[str]:
    return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]


def test_prepare_commands_bind_registration_runtime_and_gate_profile() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for field in ("registration", "creation_id", "control_directory_id", "image_digest", "gate_binding"):
        assert text.count(f"{field}:") >= 2
    assert "ManifestHandoffSupervisorEngineProfile.WRITER" in text
    assert "ManifestHandoffSupervisorEngineProfile.RECOVERY" in text
    assert "value.gate_binding.handle_id == value.registration.handle_id" in text
    assert "value.gate_binding.control_directory_id == value.control_directory_id" in text


def test_release_terminate_and_inspect_are_minimal() -> None:
    classes = _classes(DOMAIN)
    release = ast.unparse(classes["ReleaseManifestHandoffSupervisorService"])
    assert all(value in release for value in ("handle_id", "release_id", "token_artifact_id", "running_observation_id"))
    terminate = ast.unparse(classes["TerminateManifestHandoffSupervisorService"])
    assert "handle_id" in terminate and "terminate_id" in terminate
    inspect = ast.unparse(classes["InspectManifestHandoffSupervisorService"])
    assert "handle_id" in inspect
    for forbidden in ("timeout", "signal", "command", "allow", "SessionPrincipal"):
        assert forbidden not in release + terminate + inspect


def test_results_bind_journal_runtime_process_claim_owner_and_terminal() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert "value.journal.registration.handle_id != value.runtime.handle_id" in text
    assert "value.process.handle_id != value.runtime.handle_id" in text
    assert "value.process.claim_id != value.journal.registration.process_request.claim_id" in text
    assert "value.process.owner_id != value.journal.registration.process_request.owner_id" in text
    assert "value.journal.result != value.process" in text


def test_only_client_visible_journal_states_map_to_process_types() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for state in ("PREPARED_GATED", "RUNNING", "TERMINATION_REQUESTED", "TERMINAL_OBSERVED"):
        assert f"ManifestHandoffSupervisorJournalState.{state}" in text
    mapping = text[text.index("expected = {"):text.index("}.get(value.journal.state)")]
    for forbidden in ("PREPARE_REGISTERED", "LAUNCH_COMMITTED", "RELEASE_COMMITTED"):
        assert forbidden not in mapping


def test_writer_and_recovery_service_ports_are_minimal() -> None:
    classes = _classes(PORTS)
    assert _methods(classes["PersistentManifestHandoffWriterSupervisorService"]) == [
        "prepare_writer", "release_writer", "terminate_writer", "inspect_writer"]
    assert _methods(classes["PersistentManifestHandoffRecoverySupervisorService"]) == [
        "prepare_recovery", "release_recovery", "terminate_recovery", "inspect_recovery"]


def test_domain_adds_no_io_process_engine_or_authority_implementation() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for forbidden in ("open(", "Path", "os.", "subprocess", "docker", "socket", "SessionPrincipal", "Permission"):
        assert forbidden not in text
    assert "ManifestHandoffSupervisorServiceConflict" in text


def test_gate_binding_persistence_blocker_is_explicit() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "Persistenzblocker: Gatebindung" in text
    assert "Consumed- und Terminal-Artefakt-ID" in text
    assert "Productionimplementation bleibt deshalb" in text
    assert "keine neuen Artefakt-IDs erzeugen" in text
    assert "LQ-473" in text


def test_roadmap_records_lq472_and_next_gate_foundation() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-472 persistent supervisor service commands results and ports:" in roadmap
    assert "lq-472-persistent-supervisor-service-commands-results-and-ports.md" in roadmap
    assert "nächster Slice LQ-473" in roadmap
