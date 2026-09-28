import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/transport/manifest_handoff_supervisor_gate_wrapper.py"


def _text() -> str:
    return ADAPTER.read_text(encoding="utf-8")


def _methods() -> set[str]:
    tree = ast.parse(_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_adapter_implements_four_gate_operations() -> None:
    assert {"publish_ready", "await_release", "publish_consumed", "publish_terminal"} <= _methods()


def test_ready_uses_only_bound_ids_and_ready_document() -> None:
    text = _text()
    assert "ManifestHandoffSupervisorReadyDocument(" in text
    assert "request.ready_artifact_id, request.handle_id, request.gated_observation_id" in text
    assert "ReadyManifestHandoffSupervisorGateWrapper(request, publication)" in text


def test_await_reads_only_token_role_and_none_is_neutral() -> None:
    text = _text()
    assert "ManifestHandoffSupervisorControlArtifactRole.RELEASE_TOKEN" in text
    assert "if artifact is None:" in text and "return None" in text
    assert "type(document) is not ManifestHandoffSupervisorReleaseTokenDocument" in text
    assert "document.handle_id != binding.handle_id" in text


def test_consumed_uses_read_release_and_prebound_ack_identity() -> None:
    text = _text()
    assert "ManifestHandoffSupervisorReleaseConsumedDocument(" in text
    assert "binding.consumed_artifact_id, binding.handle_id, token.release_id" in text
    assert "ReleasedManifestHandoffSupervisorGateWrapper(token, publication)" in text


def test_terminal_supports_only_ready_or_released_binding() -> None:
    text = _text()
    assert "type(gate) is ReadyManifestHandoffSupervisorGateWrapper" in text
    assert "type(gate) is ReleasedManifestHandoffSupervisorGateWrapper" in text
    assert "binding.terminal_artifact_id, binding.handle_id" in text
    assert "binding.terminal_observation_id, request.outcome" in text
    assert "CompletedManifestHandoffSupervisorGateWrapper(request, publication)" in text


def test_file_conflict_is_translated_and_technical_error_is_not_none() -> None:
    text = _text()
    assert "type(result) is ManifestHandoffSupervisorControlArtifactConflict" in text
    assert "return ManifestHandoffSupervisorGateWrapperConflict()" in text
    assert "except ManifestHandoffRegistryUnavailable" in text
    assert text.count("return None") == 1


def test_no_capability_engine_file_or_authority_power() -> None:
    text = _text()
    for forbidden in ("open(", "Path", "os.", "subprocess", "Popen", "docker", "socket",
                      "SessionPrincipal", "permission", "allowed", "authorized"):
        assert forbidden not in text


def test_roadmap_records_lq466_and_next_executor_contract() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-466 file-backed manifest handoff gate wrapper:" in roadmap
    assert "lq-466-file-backed-manifest-handoff-gate-wrapper.md" in roadmap
    assert "nächster Slice LQ-467" in roadmap
