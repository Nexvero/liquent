import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_capability_outcome.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _methods(node: ast.ClassDef) -> list[str]:
    return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]


def test_inspection_requests_carry_only_existing_execution() -> None:
    classes = _classes(DOMAIN)
    writer = ast.unparse(classes["InspectManifestHandoffWriterCapabilityOutcome"])
    recovery = ast.unparse(classes["InspectManifestHandoffRecoveryCapabilityOutcome"])
    assert "execution: ExecuteManifestHandoffWriterCapability" in writer
    assert "execution: ExecuteManifestHandoffRecoveryCapability" in recovery
    for forbidden in ("timeout", "poll", "clock", "release_id", "handle_id"):
        assert forbidden not in writer + recovery


def test_writer_running_is_bound_to_handle_claim_and_owner() -> None:
    text = ast.unparse(_classes(DOMAIN)["RunningManifestHandoffWriterCapability"])
    assert "RunningManifestHandoffWriterProcess" in text
    assert "self.state.handle_id != self.inspection.execution.prepared.handle_id" in text
    assert "self.state.claim_id != self.inspection.execution.prepared.claim_id" in text
    assert "self.state.owner_id != self.inspection.execution.prepared.owner_id" in text


def test_recovery_running_is_bound_to_handle_claim_and_owner() -> None:
    text = ast.unparse(_classes(DOMAIN)["RunningManifestHandoffRecoveryCapability"])
    assert "RunningManifestHandoffRecoveryProcess" in text
    assert "self.state.handle_id != self.inspection.execution.prepared.handle_id" in text
    assert "self.state.claim_id != self.inspection.execution.prepared.claim_id" in text
    assert "self.state.owner_id != self.inspection.execution.prepared.owner_id" in text


def test_outcome_unions_are_only_running_or_executed() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert "RunningManifestHandoffWriterCapability | ExecutedManifestHandoffWriterCapability" in text
    assert "RunningManifestHandoffRecoveryCapability | ExecutedManifestHandoffRecoveryCapability" in text
    for forbidden in ("PreparedManifestHandoff", "ReadyManifestHandoff", " | None"):
        assert forbidden not in text


def test_inspection_port_is_read_only_and_profile_specific() -> None:
    classes = _classes(PORTS)
    port = classes["ManifestHandoffSupervisorCapabilityOutcomeInspection"]
    assert _methods(port) == ["inspect_writer_outcome", "inspect_recovery_outcome"]
    text = ast.unparse(port)
    for forbidden in ("release", "start", "terminate", "None"):
        assert forbidden not in text


def test_wait_port_returns_only_terminal_executed_records() -> None:
    classes = _classes(PORTS)
    port = classes["ManifestHandoffSupervisorCapabilityOutcomeWait"]
    assert _methods(port) == ["wait_writer_outcome", "wait_recovery_outcome"]
    text = ast.unparse(port)
    assert "ExecutedManifestHandoffWriterCapability" in text
    assert "ExecutedManifestHandoffRecoveryCapability" in text
    assert "RunningManifestHandoff" not in text and "None" not in text


def test_no_process_engine_file_authority_or_timing_parameters() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for forbidden in ("SessionPrincipal", "Permission", "allow", "authorized", "timeout:",
                      "sleep", "subprocess", "docker", "socket", "open(", "Path"):
        assert forbidden not in text


def test_roadmap_records_lq469_and_next_outcome_adapter() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-469 asynchronous capability outcome inspect and wait contract:" in roadmap
    assert "lq-469-asynchronous-capability-outcome-inspect-and-wait-contract.md" in roadmap
    assert "nächster Slice LQ-470" in roadmap
