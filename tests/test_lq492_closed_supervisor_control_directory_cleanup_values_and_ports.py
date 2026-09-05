import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
DOMAIN = ROOT / "src/liquent_platform/identity/manifest_handoff_supervisor_control_directory_cleanup.py"
PORTS = ROOT / "src/liquent_platform/identity/ports.py"


def _domain() -> str:
    return DOMAIN.read_text(encoding="utf-8")


def test_three_ids_are_stable_repr_free_values() -> None:
    text = _domain()
    for name in (
        "ManifestHandoffSupervisorControlDirectoryCleanupAttemptId",
        "ManifestHandoffSupervisorControlDirectoryRetentionDecisionId",
        "ManifestHandoffSupervisorControlDirectoryRetentionPolicyRevisionId",
    ):
        assert f"class {name}:" in text
    assert text.count("value: str = field(repr=False)") == 3


def test_decision_is_closed_retired_bound_and_monotone() -> None:
    text = _domain()
    assert 'RETAIN = "retain"' in text and 'ELIGIBLE = "eligible"' in text
    assert "retired: RetiredManifestHandoffSupervisorControlDirectory" in text
    assert "self.decided_at < self.retired.retired_at" in text
    assert "def directory_id(self)" in text


def test_cleanup_request_identifies_actor_and_target_without_allow_or_path() -> None:
    text = _domain()
    segment = text[text.index("class CleanupManifestHandoffSupervisorControlDirectory"):
        text.index("class ManifestHandoffSupervisorControlDirectoryCleanupOutcome")]
    for field in ("attempt_id:", "actor_user_id: UserId", "directory_id:"):
        assert field in segment
    for forbidden in ("allow", "role", "permission", "leaf", "root", "Path"):
        assert forbidden not in segment


def test_completed_outcomes_are_only_removed_and_already_absent() -> None:
    text = _domain()
    assert 'REMOVED = "removed"' in text
    assert 'ALREADY_ABSENT = "already_absent"' in text
    assert "CompletedManifestHandoffSupervisorControlDirectoryCleanup" in text
    assert "completed_at: datetime" in text


def test_unknown_effect_requires_bound_reconciliation() -> None:
    text = _domain()
    assert "class ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired" in text
    assert "class ReconcileManifestHandoffSupervisorControlDirectoryCleanup" in text
    assert 'ABSENT = "absent"' in text
    assert 'PRESENT = "present"' in text
    assert 'CONFLICT = "conflict"' in text
    assert "class ReconciledManifestHandoffSupervisorControlDirectoryCleanup" in text


def test_conflict_is_fieldless_and_domain_has_no_file_or_technical_exception() -> None:
    text = _domain()
    tree = ast.parse(text)
    conflict = next(node for node in tree.body if isinstance(node, ast.ClassDef)
        and node.name == "ManifestHandoffSupervisorControlDirectoryCleanupConflict")
    assert not [node for node in conflict.body if isinstance(node, ast.AnnAssign)]
    for forbidden in ("from pathlib", "import os", "ManifestHandoffRegistryUnavailable"):
        assert forbidden not in text


def test_ports_add_exact_decision_execution_and_reconciliation_surfaces() -> None:
    text = PORTS.read_text(encoding="utf-8")
    for cls, method in (
        ("ManifestHandoffSupervisorControlDirectoryCleanupDecisionLookup", "resolve_control_directory_cleanup_decision"),
        ("ManifestHandoffSupervisorControlDirectoryCleanupExecution", "cleanup_control_directory"),
        ("ManifestHandoffSupervisorControlDirectoryCleanupReconciliation", "reconcile_control_directory_cleanup"),
    ):
        assert f"class {cls}(Protocol):" in text
        section = text[text.index(f"class {cls}(Protocol):"):]
        assert f"def {method}(" in section


def test_no_schema_adapter_operator_or_wiring_decision() -> None:
    text = _domain()
    for forbidden in ("sqlalchemy", "CREATE TABLE", "open(", "unlink", "create_app", "argparse"):
        assert forbidden not in text


def test_roadmap_records_lq492_and_lq493() -> None:
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text(encoding="utf-8")
    assert "- LQ-492 closed supervisor control-directory cleanup values and ports:" in roadmap
    assert "lq-492-closed-supervisor-control-directory-cleanup-values-and-ports.md" in roadmap
    assert "nächster Slice LQ-493" in roadmap
