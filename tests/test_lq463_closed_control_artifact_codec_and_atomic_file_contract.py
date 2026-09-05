import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_control_artifact.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _classes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _methods(node: ast.ClassDef) -> list[str]:
    return [item.name for item in node.body if isinstance(item, ast.FunctionDef)]


def test_four_documents_fix_role_and_correlation_class() -> None:
    classes = _classes(DOMAIN)
    matrix = {
        "ManifestHandoffSupervisorReadyDocument": ("WRAPPER_READY", "GatedObservationId"),
        "ManifestHandoffSupervisorReleaseTokenDocument": ("RELEASE_TOKEN", "ReleaseId"),
        "ManifestHandoffSupervisorReleaseConsumedDocument": ("RELEASE_CONSUMED", "ReleaseId"),
        "ManifestHandoffSupervisorTerminalEnvelopeDocument": ("TERMINAL_ENVELOPE", "TerminalObservationId"),
    }
    for name, expected in matrix.items():
        text = ast.unparse(classes[name])
        assert all(value in text for value in expected)
        assert "init=False" in text


def test_terminal_envelope_is_closed_and_handle_bound() -> None:
    text = ast.unparse(_classes(DOMAIN)["ManifestHandoffSupervisorTerminalEnvelopeDocument"])
    assert "CompletedManifestHandoffWriterProcess | CompletedManifestHandoffRecoveryProcess" in text
    assert "self.outcome.handle_id != self.handle_id" in text
    for forbidden in ("payload", "log", "traceback", "exit_code"):
        assert forbidden not in text


def test_encoded_bytes_are_bounded_and_facts_are_exact() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert "MAX_MANIFEST_HANDOFF_SUPERVISOR_CONTROL_ARTIFACT_BYTES = 65_536" in text
    assert "self.facts.byte_count == len(self.content.value)" in text
    assert "hashlib.sha256(self.content.value).hexdigest()" in text


def test_ports_are_minimal_and_separate() -> None:
    classes = _classes(PORTS)
    assert _methods(classes["ManifestHandoffSupervisorControlArtifactCodec"]) == ["encode", "decode"]
    assert _methods(classes["ManifestHandoffSupervisorControlArtifactPublisher"]) == ["publish"]
    assert _methods(classes["ManifestHandoffSupervisorControlArtifactReader"]) == ["read"]


def test_publish_and_read_requests_expose_no_path_or_filename() -> None:
    classes = _classes(DOMAIN)
    request_text = ast.unparse(classes["PublishManifestHandoffSupervisorControlArtifact"])
    request_text += ast.unparse(classes["ReadManifestHandoffSupervisorControlArtifact"])
    assert "control_directory_id" in request_text
    for forbidden in ("path", "filename", "mode", "overwrite", "temporary"):
        assert forbidden not in request_text


def test_contract_has_detail_free_conflict_without_io_implementation() -> None:
    text = DOMAIN.read_text(encoding="utf-8")
    assert "class ManifestHandoffSupervisorControlArtifactConflict" in text
    for forbidden in ("open(", "os.", "Path", "tempfile", "SessionPrincipal", "subprocess"):
        assert forbidden not in text


def test_roadmap_records_lq463_and_next_adapter() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-463 closed control artifact codec and atomic file contract:" in roadmap
    assert "lq-463-closed-control-artifact-codec-and-atomic-file-contract.md" in roadmap
    assert "nächster Slice LQ-464" in roadmap
