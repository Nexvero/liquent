import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_gate_wrapper.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _methods(node: ast.ClassDef) -> list[str]:
    return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]


def test_start_binding_fixes_profile_correlations_and_unique_artifacts() -> None:
    text = ast.unparse(_classes(DOMAIN)["StartManifestHandoffSupervisorGateWrapper"])
    for field in ("handle_id", "control_directory_id", "profile", "ready_artifact_id",
                  "gated_observation_id", "consumed_artifact_id", "terminal_artifact_id",
                  "terminal_observation_id"):
        assert field in text
    assert "len({self.ready_artifact_id, self.consumed_artifact_id, self.terminal_artifact_id}) == 3" in text


def test_ready_requires_exact_durable_ready_publication() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert "ReadyManifestHandoffSupervisorGateWrapper" in text
    assert "self.binding.ready_artifact_id" in text
    assert "ManifestHandoffSupervisorControlArtifactRole.WRAPPER_READY" in text
    assert "publication.control_directory_id == binding.control_directory_id" in text


def test_token_is_only_accepted_after_ready_and_has_fresh_artifact_id() -> None:
    text = ast.unparse(_classes(DOMAIN)["AcceptedManifestHandoffSupervisorReleaseToken"])
    assert "ready: ReadyManifestHandoffSupervisorGateWrapper" in text
    assert "release_id: ManifestHandoffSupervisorReleaseId" in text
    assert "self.token_artifact_id not in" in text


def test_released_requires_consumed_publication_and_is_execution_marker() -> None:
    text = ast.unparse(_classes(DOMAIN)["ReleasedManifestHandoffSupervisorGateWrapper"])
    assert "AcceptedManifestHandoffSupervisorReleaseToken" in text
    assert "consumed_artifact_id" in text
    assert "RELEASE_CONSUMED" in text
    domain = DOMAIN.read_text(encoding="utf-8")
    for forbidden in ("allowed", "authorized", "permission", "SessionPrincipal"):
        assert forbidden not in domain


def test_terminal_accepts_ready_or_released_and_matches_profile_handle() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert "ReadyManifestHandoffSupervisorGateWrapper | ReleasedManifestHandoffSupervisorGateWrapper" in text
    complete = ast.unparse(_classes(DOMAIN)["CompleteManifestHandoffSupervisorGateWrapper"])
    assert "CompletedManifestHandoffWriterProcess" in complete
    assert "CompletedManifestHandoffRecoveryProcess" in complete
    assert "self.outcome.handle_id != binding.handle_id" in complete
    assert "binding.profile is ManifestHandoffSupervisorEngineProfile.WRITER" in complete


def test_completed_requires_bound_terminal_publication() -> None:
    text = ast.unparse(_classes(DOMAIN)["CompletedManifestHandoffSupervisorGateWrapper"])
    assert "binding.terminal_artifact_id" in text
    assert "TERMINAL_ENVELOPE" in text
    assert "_publication_matches" in text


def test_port_exposes_only_four_staged_gate_operations() -> None:
    wrapper = _classes(PORTS)["ManifestHandoffSupervisorGateWrapper"]
    assert _methods(wrapper) == ["publish_ready", "await_release", "publish_consumed", "publish_terminal"]


def test_no_file_engine_process_or_authority_implementation() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for forbidden in ("open(", "Path", "os.", "subprocess", "docker", "socket", "command:", "timeout:"):
        assert forbidden not in text
    assert "ManifestHandoffSupervisorGateWrapperConflict" in text


def test_roadmap_records_lq465_and_next_wrapper_implementation() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-465 closed manifest handoff gate wrapper contract:" in roadmap
    assert "lq-465-closed-manifest-handoff-gate-wrapper-contract.md" in roadmap
    assert "nächster Slice LQ-466" in roadmap
