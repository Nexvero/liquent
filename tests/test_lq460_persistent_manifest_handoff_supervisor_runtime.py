import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
ADAPTER = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_runtime.py"


def _methods() -> set[str]:
    tree = ast.parse(ADAPTER.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    return {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}


def test_adapter_implements_runtime_and_artifact_ports() -> None:
    assert {"bind_runtime", "resolve_runtime", "resolve_creation", "record_ready",
        "record_release_token", "record_release_consumed", "record_terminal_envelope",
        "resolve_artifact", "resolve_artifact_role"} <= _methods()


def test_runtime_binding_requires_job_and_rejects_occupied_ids() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "_JOB" in text and "_RUNTIME_OCCUPIED" in text
    assert "transaction.execute(_JOB, values).first() is None" in text
    assert "ManifestHandoffSupervisorRuntimeConflict()" in text


def test_ready_token_and_consumed_have_strict_prerequisites() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert '"launch_committed", correlate_transition=False' in text
    assert 'RELEASE_TOKEN, "release_committed"' in text
    assert "require_token=True" in text
    assert "token.correlation_id != values[\"correlation\"]" in text


def test_terminal_envelope_does_not_require_or_claim_terminal_state() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert "TERMINAL_ENVELOPE, None" in text
    assert "terminal_observed" not in text
    assert "runtime_state" not in text and "exit_code" not in text


def test_adapter_has_no_docker_file_authority_or_process_capability() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    for forbidden in ("subprocess", "Popen", "docker", "socket", "SessionPrincipal", "open("):
        assert forbidden not in text
    assert "ManifestHandoffRegistryUnavailable" in text


def test_roadmap_records_lq460_and_next_engine_contract() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-460 persistent manifest handoff supervisor runtime:" in roadmap
    assert "lq-460-persistent-manifest-handoff-supervisor-runtime.md" in roadmap
    assert "nächster Slice LQ-461" in roadmap
