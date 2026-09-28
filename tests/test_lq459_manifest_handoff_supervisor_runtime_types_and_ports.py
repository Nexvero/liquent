import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_runtime.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _methods(node: ast.ClassDef) -> list[str]:
    return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]


def test_four_repr_free_runtime_ids_and_strict_digest_exist() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert text.count("value: str = field(repr=False)") == 5
    assert 're.fullmatch(r"sha256:[0-9a-f]{64}"' in text
    assert 're.fullmatch(r"[0-9a-f]{64}"' in text


def test_roles_and_requests_are_closed_by_correlation_type() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for role in ("wrapper_ready", "release_token", "release_consumed", "terminal_envelope"):
        assert f'= "{role}"' in text
    classes = _classes(DOMAIN)
    assert "ManifestHandoffSupervisorGatedObservationId" in ast.unparse(classes["RecordManifestHandoffSupervisorReadyArtifact"])
    assert "ManifestHandoffSupervisorReleaseId" in ast.unparse(classes["RecordManifestHandoffSupervisorReleaseTokenArtifact"])
    assert "ManifestHandoffSupervisorTerminalObservationId" in ast.unparse(classes["RecordManifestHandoffSupervisorTerminalEnvelopeArtifact"])


def test_runtime_and_artifact_ports_are_minimal_and_separate() -> None:
    classes = _classes(PORTS)
    assert _methods(classes["ManifestHandoffSupervisorRuntimeBindingStore"]) == ["bind_runtime"]
    assert _methods(classes["ManifestHandoffSupervisorRuntimeBindingLookup"]) == ["resolve_runtime", "resolve_creation"]
    assert _methods(classes["ManifestHandoffSupervisorControlArtifactStore"]) == ["record_ready", "record_release_token", "record_release_consumed", "record_terminal_envelope"]
    assert _methods(classes["ManifestHandoffSupervisorControlArtifactLookup"]) == ["resolve_artifact", "resolve_artifact_role"]


def test_no_path_process_authority_or_free_payload_is_exposed() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    for forbidden in ("Path", "subprocess", "docker", "socket", "SessionPrincipal", "payload:", "command:", "timeout:"):
        assert forbidden not in text
    assert "ManifestHandoffSupervisorRuntimeConflict" in text


def test_roadmap_records_lq459_and_next_adapter() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-459 manifest handoff supervisor runtime types and ports:" in roadmap
    assert "lq-459-manifest-handoff-supervisor-runtime-types-and-ports.md" in roadmap
    assert "nächster Slice LQ-460" in roadmap
