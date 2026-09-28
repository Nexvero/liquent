import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_capability_executor.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _methods(node: ast.ClassDef) -> list[str]:
    return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]


def test_writer_requires_released_prepared_and_closed_request() -> None:
    text = ast.unparse(_classes(DOMAIN)["ExecuteManifestHandoffWriterCapability"])
    assert "gate: ReleasedManifestHandoffSupervisorGateWrapper" in text
    assert "prepared: PreparedManifestHandoffWriterProcess" in text
    assert "request: ManifestHandoffWriterSupervisorRequest" in text
    assert "ManifestHandoffSupervisorEngineProfile.WRITER" in text


def test_recovery_requires_released_prepared_and_closed_request() -> None:
    text = ast.unparse(_classes(DOMAIN)["ExecuteManifestHandoffRecoveryCapability"])
    assert "gate: ReleasedManifestHandoffSupervisorGateWrapper" in text
    assert "prepared: PreparedManifestHandoffRecoveryProcess" in text
    assert "request: ManifestHandoffRecoverySupervisorRequest" in text
    assert "ManifestHandoffSupervisorEngineProfile.RECOVERY" in text


def test_both_requests_bind_handle_claim_and_owner() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert text.count("binding.handle_id == self.prepared.handle_id") == 2
    assert text.count("self.prepared.claim_id == self.request.claim_id") == 2
    assert text.count("self.prepared.owner_id == self.request.owner_id") == 2


def test_writer_outcome_is_fully_correlated() -> None:
    text = ast.unparse(_classes(DOMAIN)["ExecutedManifestHandoffWriterCapability"])
    assert "CompletedManifestHandoffWriterProcess" in text
    assert "self.outcome.handle_id != self.execution.prepared.handle_id" in text
    assert "self.outcome.claim_id != self.execution.prepared.claim_id" in text
    assert "self.outcome.owner_id != self.execution.prepared.owner_id" in text


def test_recovery_outcome_is_fully_correlated() -> None:
    text = ast.unparse(_classes(DOMAIN)["ExecutedManifestHandoffRecoveryCapability"])
    assert "CompletedManifestHandoffRecoveryProcess" in text
    assert "self.outcome.handle_id != self.execution.prepared.handle_id" in text
    assert "self.outcome.claim_id != self.execution.prepared.claim_id" in text
    assert "self.outcome.owner_id != self.execution.prepared.owner_id" in text


def test_executor_port_has_only_two_profile_specific_methods() -> None:
    executor = _classes(PORTS)["ManifestHandoffSupervisorCapabilityExecutor"]
    assert _methods(executor) == ["execute_writer", "execute_recovery"]
    text = ast.unparse(executor)
    assert "ExecutedManifestHandoffWriterCapability" in text
    assert "ExecutedManifestHandoffRecoveryCapability" in text


def test_no_authority_process_file_or_adapter_implementation() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for forbidden in ("SessionPrincipal", "Permission", "allow", "authorized", "command:",
                      "args:", "timeout:", "subprocess", "docker", "socket", "open(", "Path"):
        assert forbidden not in text


def test_roadmap_records_lq467_and_next_executor_adapter() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-467 closed manifest handoff capability executor contract:" in roadmap
    assert "lq-467-closed-manifest-handoff-capability-executor-contract.md" in roadmap
    assert "nächster Slice LQ-468" in roadmap
