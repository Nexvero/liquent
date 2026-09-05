import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
SERVICE = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_cleanup_retention_operation.py"
STORE = ROOT / "src/liquent_platform/persistence/manifest_handoff_supervisor_cleanup_retention_operation.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _text(): return SERVICE.read_text(encoding="utf-8")


def test_composition_requires_four_closed_dependencies() -> None:
    text = _text()
    for method in ("resolve_control_directory", "evaluate_control_directory_retention",
                   "resolve_control_directory_retention_operation",
                   "bind_control_directory_retention_decision"):
        assert method in text
    assert "decision_id_generator" in text


def test_existing_operation_precedes_directory_evaluation_and_generator() -> None:
    method = _text()[_text().index("def execute("):]
    lookup = method.index("resolve_control_directory_retention_operation")
    assert lookup < method.index("resolve_control_directory(")
    assert lookup < method.index("evaluate_control_directory_retention(")
    assert lookup < method.index("self._decision()")


def test_retry_binds_same_directory_and_divergence_conflicts() -> None:
    text = _text()
    assert "existing.evaluation.request.directory_id == request.directory_id" in text
    assert "ManifestHandoffSupervisorCleanupRetentionOperationConflict()" in text


def test_only_exact_retired_lifecycle_is_evaluated() -> None:
    text = _text()
    assert "type(lifecycle) is not RetiredManifestHandoffSupervisorControlDirectory" in text
    assert "return None" in text
    assert "evaluate_control_directory_retention(request, lifecycle)" in text


def test_decision_id_is_internal_typed_and_generated_after_evaluation() -> None:
    method = _text()[_text().index("def execute("):]
    assert method.index("evaluation is None") < method.index("self._decision()")
    assert "type(decision_id) is not ManifestHandoffSupervisorControlDirectoryRetentionDecisionId" in method
    assert "BindManifestHandoffSupervisorControlDirectoryRetentionDecision(" in method


def test_store_lookup_is_read_only_and_reconstructs_bound_result() -> None:
    text = STORE.read_text(encoding="utf-8")
    section = text[text.index("def resolve_control_directory_retention_operation"):
                   text.index("@staticmethod\n    def _bound")]
    assert "_OPERATION" in section and "self._bound(row)" in section
    assert "self._read(action)" in section
    assert "INSERT " not in section and "UPDATE " not in section and "DELETE " not in section
    ports = PORTS.read_text(encoding="utf-8")
    assert "def resolve_control_directory_retention_operation(" in ports


def test_concurrent_first_writer_wins_for_same_directory_only() -> None:
    text = STORE.read_text(encoding="utf-8")
    method = ast.unparse(next(node for node in next(
        item for item in ast.parse(text).body if isinstance(item, ast.ClassDef)
    ).body if isinstance(node, ast.FunctionDef)
        and node.name == "bind_control_directory_retention_decision"))
    assert "bound.evaluation.request.directory_id == evaluation.request.directory_id" in method
    assert "bound.evaluation == evaluation" not in method
    assert method.index("existing =") < method.index("collided =")


def test_no_clearance_cleanup_operator_or_file_effect() -> None:
    text = _text()
    for forbidden in ("clearance", "cleanup_control_directory", "from pathlib",
                      "open(", "unlink", "argparse", "create_app"):
        assert forbidden not in text


def test_roadmap_records_lq540_and_lq541() -> None:
    roadmap=(ROOT/"docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-540 controlled persistent supervisor cleanup retention operation:" in roadmap
    assert "lq-540-controlled-persistent-supervisor-cleanup-retention-operation.md" in roadmap
    assert "nächster Slice LQ-541" in roadmap
